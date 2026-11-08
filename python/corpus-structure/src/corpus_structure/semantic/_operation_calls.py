"""Generated from execution call correspondences; do not edit."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Annotated, Literal, Protocol, TypedDict, cast

from pydantic import Field, JsonValue, TypeAdapter
from sqlalchemy import (
    ARRAY,
    BigInteger,
    Boolean,
    Column,
    Connection,
    DateTime,
    Integer,
    Named,
    Numeric,
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

from corpus_structure.core.vocab import TaskUnitType

from ._operation_ids import ContentDigest as ContentDigest
from ._operation_ids import CutId as CutId
from ._operation_ids import DocumentId as DocumentId
from ._operation_ids import InterventionId as InterventionId
from ._operation_ids import MethodConfigId as MethodConfigId
from ._operation_ids import MethodId as MethodId
from ._operation_ids import NativeAdmissionParametersPurpose as NativeAdmissionParametersPurpose
from ._operation_ids import PdfFrozenBuildKind as PdfFrozenBuildKind
from ._operation_ids import PdfRecordCompanionFamily as PdfRecordCompanionFamily
from ._operation_ids import PdfSourceViewPublicationMembership as PdfSourceViewPublicationMembership
from ._operation_ids import ProductKey as ProductKey
from ._operation_ids import ProjectId as ProjectId
from ._operation_ids import RealizationId as RealizationId
from ._operation_ids import ReleaseId as ReleaseId
from ._operation_ids import RunId as RunId
from ._operation_ids import RuntimeId as RuntimeId
from ._operation_ids import SourceViewId as SourceViewId
from ._operation_ids import TaskAttempt as TaskAttempt
from ._operation_ids import TaskId as TaskId
from .metadata import table as _core_table
from .operation_value_types import (
    HeldProgress,
    NativeResultViolation,
    NativeRowResult,
    OperationResult,
    held_progress,
    native_result_scope,
    native_result_value,
    require_call_context,
)
from .types import PreparedRelease


def _required[T](value: T | None, field: str, result_class: str, operation: str) -> T:
    if value is None:
        raise NativeResultViolation(operation, result_class, field)
    return value


class CompletionReceipt(OperationResult):
    task_id: TaskId
    run_id: RunId
    release_id: ReleaseId
    attempt: TaskAttempt
    protocol: Literal["done", "empty", "failed"]
    observation_ids: tuple[int, ...]
    result_digest: str


PUBLISH_RELEASE_ARCHIVE_CONTRACT_DIGEST = (
    "2db85824e49a3adb124084714d6aa98043f31fecfc34692ec01acee0edbb4dac"
)


class _publish_release_archiveRequest(OperationResult):
    payload: JsonValue


_publish_release_archive_function = func.sem.publish_release_archive(
    bindparam("payload", type_=JSONB()),
    type_=Text(),
)
_publish_release_archive_statement = select(_publish_release_archive_function)


def prepare_publish_release_archive(
    *,
    payload: JsonValue,
    projection_context: PreparedRelease | None = None,
) -> Select[str]:
    _request = _publish_release_archiveRequest(
        payload=payload,
    )
    if projection_context is not None:
        require_call_context(
            projection_context,
            "archive",
            "publish_release_archive",
            PUBLISH_RELEASE_ARCHIVE_CONTRACT_DIGEST,
        )
    return _publish_release_archive_statement.params(
        **{
            "payload": _request.payload,
        }
    )


_publish_release_archive_adapter = TypeAdapter(ReleaseId)


def materialize_publish_release_archive(row: tuple[str]) -> ReleaseId:
    with native_result_scope("archive", "publish_release_archive", "release_id"):
        checked = _publish_release_archive_adapter.validate_python(row[0], strict=True)
        return checked


def publish_release_archive(
    conn: Connection,
    *,
    payload: JsonValue,
    projection_context: PreparedRelease | None = None,
) -> ReleaseId:
    _statement = prepare_publish_release_archive(
        payload=payload,
        projection_context=projection_context,
    )
    _native_result = conn.execute(_statement)
    with native_result_scope("archive", "publish_release_archive"):
        row = _native_result.one()
        return materialize_publish_release_archive(row)


ACTIVATE_RELEASE_CONTRACT_DIGEST = (
    "bf333661e856dcc2b28beb7edb12b11b03c41efb47c9b68cb368b551b973789d"
)


class _activate_releaseRequest(OperationResult):
    project_id: ProjectId
    release_id: ReleaseId
    expected_parent: ReleaseId | None
    expected_generation: Annotated[int, Field(ge=-9223372036854775808, le=9223372036854775807)]


_activate_release_function = func.sem.activate_release(
    bindparam("project_id", type_=Text()),
    bindparam("release_id", type_=Text()),
    bindparam("expected_parent", type_=Text()),
    bindparam("expected_generation", type_=BigInteger()),
    type_=BigInteger(),
)
_activate_release_statement = select(_activate_release_function)


def prepare_activate_release(
    *,
    project_id: ProjectId,
    release_id: ReleaseId,
    expected_parent: ReleaseId | None,
    expected_generation: int,
    projection_context: PreparedRelease | None = None,
) -> Select[int]:
    _request = _activate_releaseRequest(
        project_id=project_id,
        release_id=release_id,
        expected_parent=expected_parent,
        expected_generation=expected_generation,
    )
    if projection_context is not None:
        require_call_context(
            projection_context, "activate", "activate_release", ACTIVATE_RELEASE_CONTRACT_DIGEST
        )
    return _activate_release_statement.params(
        **{
            "project_id": _request.project_id,
            "release_id": _request.release_id,
            "expected_parent": _request.expected_parent,
            "expected_generation": _request.expected_generation,
        }
    )


_activate_release_adapter = TypeAdapter(int)


def materialize_activate_release(row: tuple[int]) -> int:
    with native_result_scope("activate", "activate_release", "generation"):
        checked = _activate_release_adapter.validate_python(row[0], strict=True)
        return checked


def activate_release(
    conn: Connection,
    *,
    project_id: ProjectId,
    release_id: ReleaseId,
    expected_parent: ReleaseId | None,
    expected_generation: int,
    projection_context: PreparedRelease | None = None,
) -> int:
    _statement = prepare_activate_release(
        project_id=project_id,
        release_id=release_id,
        expected_parent=expected_parent,
        expected_generation=expected_generation,
        projection_context=projection_context,
    )
    _native_result = conn.execute(_statement)
    with native_result_scope("activate", "activate_release"):
        row = _native_result.one()
        return materialize_activate_release(row)


INITIALIZE_SOURCE_PROJECT_CONTRACT_DIGEST = (
    "3f56e05db599e6abebf00c27e444e603753a4748887fe9c9ea5b3c2da449b175"
)


class _initialize_source_projectRequest(OperationResult):
    project_id: ProjectId
    release_id: ReleaseId
    realization_id: RealizationId


_initialize_source_project_function = func.data.initialize_source_project(
    bindparam("project_id", type_=Text()),
    bindparam("release_id", type_=Text()),
    bindparam("realization_id", type_=Text()),
    type_=Text(),
)
_initialize_source_project_statement = select(_initialize_source_project_function)


def prepare_initialize_source_project(
    *,
    project_id: ProjectId,
    release_id: ReleaseId,
    realization_id: RealizationId,
    projection_context: PreparedRelease | None = None,
) -> Select[str]:
    _request = _initialize_source_projectRequest(
        project_id=project_id,
        release_id=release_id,
        realization_id=realization_id,
    )
    if projection_context is not None:
        require_call_context(
            projection_context,
            "construct_project",
            "initialize_source_project",
            INITIALIZE_SOURCE_PROJECT_CONTRACT_DIGEST,
        )
    return _initialize_source_project_statement.params(
        **{
            "project_id": _request.project_id,
            "release_id": _request.release_id,
            "realization_id": _request.realization_id,
        }
    )


_initialize_source_project_adapter = TypeAdapter(RealizationId)


def materialize_initialize_source_project(row: tuple[str]) -> RealizationId:
    with native_result_scope("construct_project", "initialize_source_project", "realization_id"):
        checked = _initialize_source_project_adapter.validate_python(row[0], strict=True)
        return checked


def initialize_source_project(
    conn: Connection,
    *,
    project_id: ProjectId,
    release_id: ReleaseId,
    realization_id: RealizationId,
    projection_context: PreparedRelease | None = None,
) -> RealizationId:
    _statement = prepare_initialize_source_project(
        project_id=project_id,
        release_id=release_id,
        realization_id=realization_id,
        projection_context=projection_context,
    )
    _native_result = conn.execute(_statement)
    with native_result_scope("construct_project", "initialize_source_project"):
        row = _native_result.one()
        return materialize_initialize_source_project(row)


REGISTER_RUNTIME_BINDING_CONTRACT_DIGEST = (
    "f0ee952a1b7c29e55dbd885373e6ca893b882317aa1a88ae2e35a0ee6d618e99"
)


class _register_runtime_bindingRequest(OperationResult):
    release_id: ReleaseId
    runtime_id: RuntimeId
    manifest: bytes
    archive: bytes


_register_runtime_binding_function = func.sem.register_runtime_binding(
    bindparam("release_id", type_=Text()),
    bindparam("runtime_id", type_=Text()),
    bindparam("manifest", type_=BYTEA()),
    bindparam("archive", type_=BYTEA()),
    type_=Text(),
)
_register_runtime_binding_statement = select(_register_runtime_binding_function)


def prepare_register_runtime_binding(
    *,
    release_id: ReleaseId,
    runtime_id: RuntimeId,
    manifest: bytes,
    archive: bytes,
    projection_context: PreparedRelease | None = None,
) -> Select[str]:
    _request = _register_runtime_bindingRequest(
        release_id=release_id,
        runtime_id=runtime_id,
        manifest=manifest,
        archive=archive,
    )
    if projection_context is not None:
        require_call_context(
            projection_context,
            "start_run",
            "register_runtime_binding",
            REGISTER_RUNTIME_BINDING_CONTRACT_DIGEST,
        )
    return _register_runtime_binding_statement.params(
        **{
            "release_id": _request.release_id,
            "runtime_id": _request.runtime_id,
            "manifest": _request.manifest,
            "archive": _request.archive,
        }
    )


_register_runtime_binding_adapter = TypeAdapter(RuntimeId)


def materialize_register_runtime_binding(row: tuple[str]) -> RuntimeId:
    with native_result_scope("start_run", "register_runtime_binding", "runtime_id"):
        checked = _register_runtime_binding_adapter.validate_python(row[0], strict=True)
        return checked


def register_runtime_binding(
    conn: Connection,
    *,
    release_id: ReleaseId,
    runtime_id: RuntimeId,
    manifest: bytes,
    archive: bytes,
    projection_context: PreparedRelease | None = None,
) -> RuntimeId:
    _statement = prepare_register_runtime_binding(
        release_id=release_id,
        runtime_id=runtime_id,
        manifest=manifest,
        archive=archive,
        projection_context=projection_context,
    )
    _native_result = conn.execute(_statement)
    with native_result_scope("start_run", "register_runtime_binding"):
        row = _native_result.one()
        return materialize_register_runtime_binding(row)


CREATE_RUN_CONTRACT_DIGEST = "f51b77ef54c54a01fedcd69ad2ba5893e3964b126a26e6a7d63f6e565f10922a"


class _create_runRequest(OperationResult):
    project_id: ProjectId
    release_id: ReleaseId
    runtime_id: RuntimeId
    realization_id: RealizationId
    revision: Annotated[int, Field(ge=-9223372036854775808, le=9223372036854775807)]
    dependencies: bytes
    kind: str
    phase: Annotated[int, Field(ge=-9223372036854775808, le=9223372036854775807)]
    options: JsonValue
    guideline: str
    code_commit: str


_create_run_function = func.ops.create_run(
    bindparam("project_id", type_=Text()),
    bindparam("release_id", type_=Text()),
    bindparam("runtime_id", type_=Text()),
    bindparam("realization_id", type_=Text()),
    bindparam("revision", type_=BigInteger()),
    bindparam("dependencies", type_=BYTEA()),
    bindparam("kind", type_=Text()),
    bindparam("phase", type_=BigInteger()),
    bindparam("options", type_=JSONB()),
    bindparam("guideline", type_=Text()),
    bindparam("code_commit", type_=Text()),
    type_=BigInteger(),
)
_create_run_statement = select(_create_run_function)


def prepare_create_run(
    *,
    project_id: ProjectId,
    release_id: ReleaseId,
    runtime_id: RuntimeId,
    realization_id: RealizationId,
    revision: int,
    dependencies: bytes,
    kind: str,
    phase: int,
    options: JsonValue,
    guideline: str,
    code_commit: str,
    projection_context: PreparedRelease | None = None,
) -> Select[int]:
    _request = _create_runRequest(
        project_id=project_id,
        release_id=release_id,
        runtime_id=runtime_id,
        realization_id=realization_id,
        revision=revision,
        dependencies=dependencies,
        kind=kind,
        phase=phase,
        options=options,
        guideline=guideline,
        code_commit=code_commit,
    )
    if projection_context is not None:
        require_call_context(
            projection_context, "start_run", "create_run", CREATE_RUN_CONTRACT_DIGEST
        )
    return _create_run_statement.params(
        **{
            "project_id": _request.project_id,
            "release_id": _request.release_id,
            "runtime_id": _request.runtime_id,
            "realization_id": _request.realization_id,
            "revision": _request.revision,
            "dependencies": _request.dependencies,
            "kind": _request.kind,
            "phase": _request.phase,
            "options": _request.options,
            "guideline": _request.guideline,
            "code_commit": _request.code_commit,
        }
    )


_create_run_adapter = TypeAdapter(RunId)


def materialize_create_run(row: tuple[int]) -> RunId:
    with native_result_scope("start_run", "create_run", "run_id"):
        checked = _create_run_adapter.validate_python(row[0], strict=True)
        return checked


def create_run(
    conn: Connection,
    *,
    project_id: ProjectId,
    release_id: ReleaseId,
    runtime_id: RuntimeId,
    realization_id: RealizationId,
    revision: int,
    dependencies: bytes,
    kind: str,
    phase: int,
    options: JsonValue,
    guideline: str,
    code_commit: str,
    projection_context: PreparedRelease | None = None,
) -> RunId:
    _statement = prepare_create_run(
        project_id=project_id,
        release_id=release_id,
        runtime_id=runtime_id,
        realization_id=realization_id,
        revision=revision,
        dependencies=dependencies,
        kind=kind,
        phase=phase,
        options=options,
        guideline=guideline,
        code_commit=code_commit,
        projection_context=projection_context,
    )
    _native_result = conn.execute(_statement)
    with native_result_scope("start_run", "create_run"):
        row = _native_result.one()
        return materialize_create_run(row)


METHOD_DEFINITION_CONTRACT_DIGEST = (
    "ba21fbc400515fa728f561a1fefb694423bfe8576ba00064a033073e64d147cb"
)


class RecordedMethod(NativeRowResult):
    id: MethodId
    name: str
    version: str
    unit_type: str | None
    configuration_schema_digest: str | None
    family: str
    tier: str
    confidence_source: str | None


class _method_definitionRequest(OperationResult):
    name: str
    version: str
    unit_type: str | None
    configuration_schema_digest: str | None
    family: str
    tier: str
    confidence_source: str | None


def prepare_method_definition(
    *,
    name: str,
    version: str,
    unit_type: str | None,
    configuration_schema_digest: str | None,
    family: str,
    tier: str,
    confidence_source: str | None,
    projection_context: PreparedRelease,
) -> _method_definitionRequest:
    _request = _method_definitionRequest(
        name=name,
        version=version,
        unit_type=unit_type,
        configuration_schema_digest=configuration_schema_digest,
        family=family,
        tier=tier,
        confidence_source=confidence_source,
    )
    require_call_context(
        projection_context,
        "configure_method",
        "method_definition",
        METHOD_DEFINITION_CONTRACT_DIGEST,
    )
    return _request


class MethodDefinitionOpsMethodValues(TypedDict):
    name: str
    version: str
    unit_type: str | None
    configuration_schema_digest: str | None
    family: str
    tier: str
    confidence_source: str | None


def values_method_definition_ops_method(
    request: _method_definitionRequest,
) -> MethodDefinitionOpsMethodValues:
    return {
        "name": request.name,
        "version": request.version,
        "unit_type": request.unit_type,
        "configuration_schema_digest": request.configuration_schema_digest,
        "family": request.family,
        "tier": request.tier,
        "confidence_source": request.confidence_source,
    }


class MethodDefinitionOpsMethodValuesExpected(TypedDict):
    name: str
    version: str
    unit_type: str | None
    configuration_schema_digest: str | None
    family: str
    tier: str
    confidence_source: str | None


def expected_method_definition_ops_method(
    request: _method_definitionRequest,
) -> MethodDefinitionOpsMethodValuesExpected:
    return {
        "name": request.name,
        "version": request.version,
        "unit_type": request.unit_type,
        "configuration_schema_digest": request.configuration_schema_digest,
        "family": request.family,
        "tier": request.tier,
        "confidence_source": request.confidence_source,
    }


class _method_definition_ops_methodColumns(TypedColumns):
    id: Named[int]
    name: Named[str]
    version: Named[str]
    unit_type: Named[str | None]
    configuration_schema_digest: Named[str | None]
    family: Named[str]
    tier: Named[str]
    confidence_source: Named[str | None]


class _method_definition_ops_methodColumnsProtocol(Protocol):
    id: Column[int]
    name: Column[str]
    version: Column[str]
    unit_type: Column[str | None]
    configuration_schema_digest: Column[str | None]
    family: Column[str]
    tier: Column[str]
    confidence_source: Column[str | None]


_method_definition_ops_method = _core_table("ops.method").with_cols(
    _method_definition_ops_methodColumns
)
_method_definition_ops_method_columns = cast(
    _method_definition_ops_methodColumnsProtocol, _method_definition_ops_method.c
)

projection_method_definition: tuple[
    ColumnElement[int],
    ColumnElement[str],
    ColumnElement[str],
    ColumnElement[str | None],
    ColumnElement[str | None],
    ColumnElement[str],
    ColumnElement[str],
    ColumnElement[str | None],
] = (
    _method_definition_ops_method_columns.id.label("id"),
    _method_definition_ops_method_columns.name.label("name"),
    _method_definition_ops_method_columns.version.label("version"),
    _method_definition_ops_method_columns.unit_type.label("unit_type"),
    _method_definition_ops_method_columns.configuration_schema_digest.label(
        "configuration_schema_digest"
    ),
    _method_definition_ops_method_columns.family.label("family"),
    _method_definition_ops_method_columns.tier.label("tier"),
    _method_definition_ops_method_columns.confidence_source.label("confidence_source"),
)


def materialize_method_definition(
    row: tuple[int, str, str, str | None, str | None, str, str, str | None],
) -> RecordedMethod:
    with native_result_scope("configure_method", "RecordedMethod"):
        return RecordedMethod(
            id=MethodId(row[0]),
            name=row[1],
            version=row[2],
            unit_type=row[3],
            configuration_schema_digest=row[4],
            family=row[5],
            tier=row[6],
            confidence_source=row[7],
        )


def collect_method_definition(
    result: Result[int, str, str, str | None, str | None, str, str, str | None],
) -> RecordedMethod:
    with native_result_scope("configure_method", "RecordedMethod"):
        return materialize_method_definition(result.one())


METHOD_CONFIGURATION_CONTRACT_DIGEST = (
    "2f763992db2e8389f8ec80df475d243ab5dd7effa2ad09f993884b1c9971967f"
)


class RecordedMethodConfig(NativeRowResult):
    __json_fields__ = ("params",)
    id: MethodConfigId
    method_id: MethodId
    name: str
    params: str
    config_hash: str


class _method_configurationRequest(OperationResult):
    method_id: Annotated[
        MethodId, Field(ge=MethodId(-9223372036854775808), le=MethodId(9223372036854775807))
    ]
    name: str
    params: JsonValue
    config_hash: str


def prepare_method_configuration(
    *,
    method_id: MethodId,
    name: str,
    params: JsonValue,
    config_hash: str,
    projection_context: PreparedRelease | None = None,
) -> _method_configurationRequest:
    _request = _method_configurationRequest(
        method_id=method_id,
        name=name,
        params=params,
        config_hash=config_hash,
    )
    if projection_context is not None:
        require_call_context(
            projection_context,
            "configure_method",
            "method_configuration",
            METHOD_CONFIGURATION_CONTRACT_DIGEST,
        )
    return _request


class MethodConfigurationOpsMethodConfigValues(TypedDict):
    method_id: MethodId
    name: str
    params: JsonValue
    config_hash: str


def values_method_configuration_ops_method_config(
    request: _method_configurationRequest,
) -> MethodConfigurationOpsMethodConfigValues:
    return {
        "method_id": request.method_id,
        "name": request.name,
        "params": request.params,
        "config_hash": request.config_hash,
    }


class MethodConfigurationOpsMethodConfigValuesExpected(TypedDict):
    method_id: MethodId
    name: str
    params: JsonValue
    config_hash: str


def expected_method_configuration_ops_method_config(
    request: _method_configurationRequest,
) -> MethodConfigurationOpsMethodConfigValuesExpected:
    return {
        "method_id": request.method_id,
        "name": request.name,
        "params": request.params,
        "config_hash": request.config_hash,
    }


class _method_configuration_ops_method_configColumns(TypedColumns):
    id: Named[int]
    method_id: Named[int]
    name: Named[str]
    params: Named[JsonValue]
    config_hash: Named[str]


class _method_configuration_ops_method_configColumnsProtocol(Protocol):
    id: Column[int]
    method_id: Column[int]
    name: Column[str]
    params: Column[JsonValue]
    config_hash: Column[str]


_method_configuration_ops_method_config = _core_table("ops.method_config").with_cols(
    _method_configuration_ops_method_configColumns
)
_method_configuration_ops_method_config_columns = cast(
    _method_configuration_ops_method_configColumnsProtocol,
    _method_configuration_ops_method_config.c,
)

projection_method_configuration: tuple[
    ColumnElement[int],
    ColumnElement[int],
    ColumnElement[str],
    ColumnElement[str],
    ColumnElement[str],
] = (
    _method_configuration_ops_method_config_columns.id.label("id"),
    _method_configuration_ops_method_config_columns.method_id.label("method_id"),
    _method_configuration_ops_method_config_columns.name.label("name"),
    _method_configuration_ops_method_config_columns.params.cast(Text()).label("params"),
    _method_configuration_ops_method_config_columns.config_hash.label("config_hash"),
)


def materialize_method_configuration(row: tuple[int, int, str, str, str]) -> RecordedMethodConfig:
    with native_result_scope("configure_method", "RecordedMethodConfig"):
        return RecordedMethodConfig(
            id=MethodConfigId(row[0]),
            method_id=MethodId(row[1]),
            name=row[2],
            params=row[3],
            config_hash=row[4],
        )


def collect_method_configuration(result: Result[int, int, str, str, str]) -> RecordedMethodConfig:
    with native_result_scope("configure_method", "RecordedMethodConfig"):
        return materialize_method_configuration(result.one())


LOCK_SCHEDULE_RUN_CONTRACT_DIGEST = (
    "63eb42e2a0203c4df7039c8af589de8779e6aaa3e7009cf6257977fec89599b9"
)


class LockedScheduleRun(NativeRowResult):
    __json_fields__ = ("options",)
    id: int
    project_id: str
    release_id: str
    runtime_id: str | None
    input_realization_id: str
    input_revision: int
    dependency_digest: str
    dependencies: bytes
    kind: str
    phase: int
    options: str
    guideline: str
    status: str
    code_commit: str
    result_realization_id: str | None
    sealed: bool


class _lock_schedule_runRequest(OperationResult):
    run_id: Annotated[RunId, Field(ge=RunId(-9223372036854775808), le=RunId(9223372036854775807))]
    operation: str = "schedule"


_lock_schedule_run_function = func.ops.lock_execution_run(
    bindparam("run_id", type_=BigInteger()),
    bindparam("operation", type_=Text()),
).table_valued(
    column("id", BigInteger()),
    column("project_id", Text()),
    column("release_id", Text()),
    column("runtime_id", Text()),
    column("input_realization_id", Text()),
    column("input_revision", BigInteger()),
    column("dependency_digest", Text()),
    column("dependencies", BYTEA()),
    column("kind", Text()),
    column("phase", BigInteger()),
    column("options", JSONB()),
    column("guideline", Text()),
    column("status", Text()),
    column("code_commit", Text()),
    column("result_realization_id", Text()),
    column("sealed", Boolean()),
)


class _lock_schedule_runColumns(Protocol):
    id: Column[int]
    project_id: Column[str]
    release_id: Column[str]
    runtime_id: Column[str | None]
    input_realization_id: Column[str]
    input_revision: Column[int]
    dependency_digest: Column[str]
    dependencies: Column[bytes]
    kind: Column[str]
    phase: Column[int]
    options: Column[JsonValue]
    guideline: Column[str]
    status: Column[str]
    code_commit: Column[str]
    result_realization_id: Column[str | None]
    sealed: Column[bool]


_lock_schedule_run_columns = cast(_lock_schedule_runColumns, _lock_schedule_run_function.c)
_lock_schedule_run_statement = select(
    _lock_schedule_run_columns.id,
    _lock_schedule_run_columns.project_id,
    _lock_schedule_run_columns.release_id,
    _lock_schedule_run_columns.runtime_id,
    _lock_schedule_run_columns.input_realization_id,
    _lock_schedule_run_columns.input_revision,
    _lock_schedule_run_columns.dependency_digest,
    _lock_schedule_run_columns.dependencies,
    _lock_schedule_run_columns.kind,
    _lock_schedule_run_columns.phase,
    _lock_schedule_run_columns.options.cast(Text()).label("options"),
    _lock_schedule_run_columns.guideline,
    _lock_schedule_run_columns.status,
    _lock_schedule_run_columns.code_commit,
    _lock_schedule_run_columns.result_realization_id,
    _lock_schedule_run_columns.sealed,
)


def _lock_schedule_run_result(
    row: tuple[
        int,
        str,
        str,
        str | None,
        str,
        int,
        str,
        bytes,
        str,
        int,
        str,
        str,
        str,
        str,
        str | None,
        bool,
    ],
) -> LockedScheduleRun:
    with native_result_scope("schedule", "LockedScheduleRun"):
        return LockedScheduleRun(
            id=row[0],
            project_id=row[1],
            release_id=row[2],
            runtime_id=row[3],
            input_realization_id=row[4],
            input_revision=row[5],
            dependency_digest=row[6],
            dependencies=row[7],
            kind=row[8],
            phase=row[9],
            options=row[10],
            guideline=row[11],
            status=row[12],
            code_commit=row[13],
            result_realization_id=row[14],
            sealed=row[15],
        )


def prepare_lock_schedule_run(
    *,
    run_id: RunId,
    operation: str = "schedule",
    projection_context: PreparedRelease | None = None,
) -> Select[
    int, str, str, str | None, str, int, str, bytes, str, int, str, str, str, str, str | None, bool
]:
    _request = _lock_schedule_runRequest(
        run_id=run_id,
        operation=operation,
    )
    if projection_context is not None:
        require_call_context(
            projection_context, "schedule", "lock_schedule_run", LOCK_SCHEDULE_RUN_CONTRACT_DIGEST
        )
    return _lock_schedule_run_statement.params(
        **{
            "run_id": _request.run_id,
            "operation": _request.operation,
        }
    )


materialize_lock_schedule_run = _lock_schedule_run_result


def lock_schedule_run(
    conn: Connection,
    *,
    run_id: RunId,
    operation: str = "schedule",
    projection_context: PreparedRelease | None = None,
) -> LockedScheduleRun:
    _statement = prepare_lock_schedule_run(
        run_id=run_id,
        operation=operation,
        projection_context=projection_context,
    )
    _native_result = conn.execute(_statement)
    with native_result_scope("schedule", "LockedScheduleRun"):
        return _lock_schedule_run_result(_native_result.one())


CLAIM_TASKS_CONTRACT_DIGEST = "dfb0ece50336eb7891ae515949b2e85b415824c7ccf9a1a209aa2fd1395bc03f"


class ClaimedTask(NativeRowResult):
    task_id: TaskId
    run_id: RunId
    release_id: ReleaseId
    method_config_id: MethodConfigId
    unit_type: TaskUnitType
    unit_id: int | None
    unit_key: str | None
    packet_hash: str | None
    attempt: TaskAttempt
    holder: str
    deadline: datetime
    invocation_key: str
    held_progress: HeldProgress | None


class _claim_tasksRequest(OperationResult):
    run_id: Annotated[RunId, Field(ge=RunId(-9223372036854775808), le=RunId(9223372036854775807))]
    config_id: Annotated[
        MethodConfigId,
        Field(ge=MethodConfigId(-9223372036854775808), le=MethodConfigId(9223372036854775807)),
    ]
    holder: str
    limit: Annotated[int, Field(ge=-9223372036854775808, le=9223372036854775807)] = 1
    agent: bool = False


_claim_tasks_function = func.ops.claim_tasks(
    bindparam("run_id", type_=BigInteger()),
    bindparam("config_id", type_=BigInteger()),
    bindparam("holder", type_=Text()),
    bindparam("limit", type_=BigInteger()),
    bindparam("agent", type_=Boolean()),
).table_valued(
    column("id", BigInteger()),
    column("run_id", BigInteger()),
    column("release_id", Text()),
    column("method_config_id", BigInteger()),
    column("unit_type", Text()),
    column("unit_id", BigInteger()),
    column("unit_key", Text()),
    column("packet_hash", Text()),
    column("attempt", BigInteger()),
    column("claimed_by", Text()),
    column("lease_until", DateTime(timezone=True)),
    column("invocation_key", Text()),
    column("error", JSONB(none_as_null=True)),
)


class _claim_tasksColumns(Protocol):
    id: Column[int]
    run_id: Column[int]
    release_id: Column[str]
    method_config_id: Column[int]
    unit_type: Column[str]
    unit_id: Column[int | None]
    unit_key: Column[str | None]
    packet_hash: Column[str | None]
    attempt: Column[int]
    claimed_by: Column[str | None]
    lease_until: Column[datetime | None]
    invocation_key: Column[str]
    error: Column[JsonValue]


_claim_tasks_columns = cast(_claim_tasksColumns, _claim_tasks_function.c)
_claim_tasks_statement = select(
    _claim_tasks_columns.id,
    _claim_tasks_columns.run_id,
    _claim_tasks_columns.release_id,
    _claim_tasks_columns.method_config_id,
    _claim_tasks_columns.unit_type,
    _claim_tasks_columns.unit_id,
    _claim_tasks_columns.unit_key,
    _claim_tasks_columns.packet_hash,
    _claim_tasks_columns.attempt,
    _claim_tasks_columns.claimed_by,
    _claim_tasks_columns.lease_until,
    _claim_tasks_columns.invocation_key,
    _claim_tasks_columns.error,
)


def _claim_tasks_result(
    row: tuple[
        int,
        int,
        str,
        int,
        str,
        int | None,
        str | None,
        str | None,
        int,
        str | None,
        datetime | None,
        str,
        JsonValue,
    ],
) -> ClaimedTask:
    with native_result_scope("claim", "ClaimedTask"):
        return ClaimedTask(
            task_id=TaskId(row[0]),
            run_id=RunId(row[1]),
            release_id=ReleaseId(row[2]),
            method_config_id=MethodConfigId(row[3]),
            unit_type=native_result_value(
                "claim", "ClaimedTask", "unit_type", TaskUnitType, row[4]
            ),
            unit_id=row[5],
            unit_key=row[6],
            packet_hash=row[7],
            attempt=TaskAttempt(row[8]),
            holder=_required(row[9], "holder", "ClaimedTask", "claim"),
            deadline=_required(row[10], "deadline", "ClaimedTask", "claim"),
            invocation_key=row[11],
            held_progress=native_result_value(
                "claim", "ClaimedTask", "held_progress", held_progress, row[12]
            ),
        )


def prepare_claim_tasks(
    *,
    run_id: RunId,
    config_id: MethodConfigId,
    holder: str,
    limit: int = 1,
    agent: bool = False,
    projection_context: PreparedRelease | None = None,
) -> Select[
    int,
    int,
    str,
    int,
    str,
    int | None,
    str | None,
    str | None,
    int,
    str | None,
    datetime | None,
    str,
    JsonValue,
]:
    _request = _claim_tasksRequest(
        run_id=run_id,
        config_id=config_id,
        holder=holder,
        limit=limit,
        agent=agent,
    )
    if projection_context is not None:
        require_call_context(
            projection_context, "claim", "claim_tasks", CLAIM_TASKS_CONTRACT_DIGEST
        )
    return _claim_tasks_statement.params(
        **{
            "run_id": _request.run_id,
            "config_id": _request.config_id,
            "holder": _request.holder,
            "limit": _request.limit,
            "agent": _request.agent,
        }
    )


materialize_claim_tasks = _claim_tasks_result


def claim_tasks(
    conn: Connection,
    *,
    run_id: RunId,
    config_id: MethodConfigId,
    holder: str,
    limit: int = 1,
    agent: bool = False,
    projection_context: PreparedRelease | None = None,
) -> tuple[ClaimedTask, ...]:
    _statement = prepare_claim_tasks(
        run_id=run_id,
        config_id=config_id,
        holder=holder,
        limit=limit,
        agent=agent,
        projection_context=projection_context,
    )
    _native_result = conn.execute(_statement)
    with native_result_scope("claim", "ClaimedTask"):
        return tuple(_claim_tasks_result(row) for row in _native_result)


COMPLETE_TASK_CONTRACT_DIGEST = "046aabc7da4e16dac54081bd194af10b88c658fdf63f6041bdfa47ed1773b569"


class CompletionResult(OperationResult):
    receipt: CompletionReceipt
    transaction: Literal["applied", "replay"]


class _complete_taskRequest(OperationResult):
    task_id: Annotated[
        TaskId, Field(ge=TaskId(-9223372036854775808), le=TaskId(9223372036854775807))
    ]
    attempt: Annotated[
        TaskAttempt,
        Field(ge=TaskAttempt(-9223372036854775808), le=TaskAttempt(9223372036854775807)),
    ]
    holder: str
    rows: JsonValue
    outcome: str
    error: JsonValue
    envelope: JsonValue | None


_complete_task_function = func.ops.complete_task(
    bindparam("task_id", type_=BigInteger()),
    bindparam("attempt", type_=BigInteger()),
    bindparam("holder", type_=Text()),
    bindparam("rows", type_=JSONB()),
    bindparam("outcome", type_=Text()),
    bindparam("error", type_=JSONB()),
    bindparam("envelope", type_=JSONB(none_as_null=True)),
    type_=JSONB(),
)
_complete_task_statement = select(_complete_task_function.cast(Text()))


def prepare_complete_task(
    *,
    task_id: TaskId,
    attempt: TaskAttempt,
    holder: str,
    rows: JsonValue,
    outcome: str,
    error: JsonValue,
    envelope: JsonValue | None,
    projection_context: PreparedRelease | None = None,
) -> Select[str]:
    _request = _complete_taskRequest(
        task_id=task_id,
        attempt=attempt,
        holder=holder,
        rows=rows,
        outcome=outcome,
        error=error,
        envelope=envelope,
    )
    if projection_context is not None:
        require_call_context(
            projection_context, "complete", "complete_task", COMPLETE_TASK_CONTRACT_DIGEST
        )
    return _complete_task_statement.params(
        **{
            "task_id": _request.task_id,
            "attempt": _request.attempt,
            "holder": _request.holder,
            "rows": _request.rows,
            "outcome": _request.outcome,
            "error": _request.error,
            "envelope": _request.envelope,
        }
    )


def complete_task(
    conn: Connection,
    *,
    task_id: TaskId,
    attempt: TaskAttempt,
    holder: str,
    rows: JsonValue,
    outcome: str,
    error: JsonValue,
    envelope: JsonValue | None,
    projection_context: PreparedRelease | None = None,
) -> CompletionResult:
    _statement = prepare_complete_task(
        task_id=task_id,
        attempt=attempt,
        holder=holder,
        rows=rows,
        outcome=outcome,
        error=error,
        envelope=envelope,
        projection_context=projection_context,
    )
    _native_result = conn.execute(_statement)
    with native_result_scope("complete", "CompletionResult"):
        value = _native_result.scalar_one()
        return CompletionResult.model_validate_json(value, strict=True)


LOCK_COMPLETE_UNIT_RUN_CONTRACT_DIGEST = (
    "932741e1b1930c8efe28c5c84d178ce0d661ac19824e374c5c87dbe5272240a3"
)


class LockedRunIdentity(NativeRowResult):
    run_id: RunId


class _lock_complete_unit_runRequest(OperationResult):
    run_id: Annotated[RunId, Field(ge=RunId(-9223372036854775808), le=RunId(9223372036854775807))]
    operation: str = "complete_unit"


_lock_complete_unit_run_function = func.ops.lock_execution_run(
    bindparam("run_id", type_=BigInteger()),
    bindparam("operation", type_=Text()),
).table_valued(
    column("id", BigInteger()),
)


class _lock_complete_unit_runColumns(Protocol):
    id: Column[int]


_lock_complete_unit_run_columns = cast(
    _lock_complete_unit_runColumns, _lock_complete_unit_run_function.c
)
_lock_complete_unit_run_statement = select(
    _lock_complete_unit_run_columns.id,
)


def _lock_complete_unit_run_result(row: tuple[int]) -> LockedRunIdentity:
    with native_result_scope("complete_unit", "LockedRunIdentity"):
        return LockedRunIdentity(
            run_id=RunId(row[0]),
        )


def prepare_lock_complete_unit_run(
    *,
    run_id: RunId,
    operation: str = "complete_unit",
    projection_context: PreparedRelease | None = None,
) -> Select[int]:
    _request = _lock_complete_unit_runRequest(
        run_id=run_id,
        operation=operation,
    )
    if projection_context is not None:
        require_call_context(
            projection_context,
            "complete_unit",
            "lock_complete_unit_run",
            LOCK_COMPLETE_UNIT_RUN_CONTRACT_DIGEST,
        )
    return _lock_complete_unit_run_statement.params(
        **{
            "run_id": _request.run_id,
            "operation": _request.operation,
        }
    )


materialize_lock_complete_unit_run = _lock_complete_unit_run_result


def lock_complete_unit_run(
    conn: Connection,
    *,
    run_id: RunId,
    operation: str = "complete_unit",
    projection_context: PreparedRelease | None = None,
) -> LockedRunIdentity:
    _statement = prepare_lock_complete_unit_run(
        run_id=run_id,
        operation=operation,
        projection_context=projection_context,
    )
    _native_result = conn.execute(_statement)
    with native_result_scope("complete_unit", "LockedRunIdentity"):
        return _lock_complete_unit_run_result(_native_result.one())


HOLD_AGENT_RESULT_CONTRACT_DIGEST = (
    "75e1b7052a6a4c6604f9a8ae172f9ff86a706312b06c9d4a7c362f412ab5d103"
)


class _hold_agent_resultRequest(OperationResult):
    task_id: Annotated[
        TaskId, Field(ge=TaskId(-9223372036854775808), le=TaskId(9223372036854775807))
    ]
    attempt: Annotated[
        TaskAttempt,
        Field(ge=TaskAttempt(-9223372036854775808), le=TaskAttempt(9223372036854775807)),
    ]
    holder: str
    packet_hash: str
    clean: bool
    result: JsonValue


_hold_agent_result_function = func.ops.hold_agent_result(
    bindparam("task_id", type_=BigInteger()),
    bindparam("attempt", type_=BigInteger()),
    bindparam("holder", type_=Text()),
    bindparam("packet_hash", type_=Text()),
    bindparam("clean", type_=Boolean()),
    bindparam("result", type_=JSONB()),
    type_=Boolean(),
)
_hold_agent_result_statement = select(_hold_agent_result_function)


def prepare_hold_agent_result(
    *,
    task_id: TaskId,
    attempt: TaskAttempt,
    holder: str,
    packet_hash: str,
    clean: bool,
    result: JsonValue,
    projection_context: PreparedRelease | None = None,
) -> Select[bool]:
    _request = _hold_agent_resultRequest(
        task_id=task_id,
        attempt=attempt,
        holder=holder,
        packet_hash=packet_hash,
        clean=clean,
        result=result,
    )
    if projection_context is not None:
        require_call_context(
            projection_context,
            "hold_submission",
            "hold_agent_result",
            HOLD_AGENT_RESULT_CONTRACT_DIGEST,
        )
    return _hold_agent_result_statement.params(
        **{
            "task_id": _request.task_id,
            "attempt": _request.attempt,
            "holder": _request.holder,
            "packet_hash": _request.packet_hash,
            "clean": _request.clean,
            "result": _request.result,
        }
    )


_hold_agent_result_adapter = TypeAdapter(bool)


def materialize_hold_agent_result(row: tuple[bool]) -> bool:
    with native_result_scope("hold_submission", "hold_agent_result", "held"):
        checked = _hold_agent_result_adapter.validate_python(row[0], strict=True)
        return checked


def hold_agent_result(
    conn: Connection,
    *,
    task_id: TaskId,
    attempt: TaskAttempt,
    holder: str,
    packet_hash: str,
    clean: bool,
    result: JsonValue,
    projection_context: PreparedRelease | None = None,
) -> bool:
    _statement = prepare_hold_agent_result(
        task_id=task_id,
        attempt=attempt,
        holder=holder,
        packet_hash=packet_hash,
        clean=clean,
        result=result,
        projection_context=projection_context,
    )
    _native_result = conn.execute(_statement)
    with native_result_scope("hold_submission", "hold_agent_result"):
        row = _native_result.one()
        return materialize_hold_agent_result(row)


LOCK_INPUT_SNAPSHOT_CONTRACT_DIGEST = (
    "28d9dcc7ffe759c0d1587c0ece1afac8989518a1e139a858df5c9527752282e7"
)


class _lock_input_snapshotRequest(OperationResult):
    run_id: Annotated[RunId, Field(ge=RunId(-9223372036854775808), le=RunId(9223372036854775807))]


_lock_input_snapshot_function = func.ops.lock_input_snapshot(
    bindparam("run_id", type_=BigInteger()),
)
_lock_input_snapshot_statement = select(_lock_input_snapshot_function)


def prepare_lock_input_snapshot(
    *,
    run_id: RunId,
    projection_context: PreparedRelease | None = None,
) -> Select[None]:
    _request = _lock_input_snapshotRequest(
        run_id=run_id,
    )
    if projection_context is not None:
        require_call_context(
            projection_context,
            "hold_submission",
            "lock_input_snapshot",
            LOCK_INPUT_SNAPSHOT_CONTRACT_DIGEST,
        )
    return _lock_input_snapshot_statement.params(
        **{
            "run_id": _request.run_id,
        }
    )


def lock_input_snapshot(
    conn: Connection,
    *,
    run_id: RunId,
    projection_context: PreparedRelease | None = None,
) -> None:
    _statement = prepare_lock_input_snapshot(
        run_id=run_id,
        projection_context=projection_context,
    )
    _native_result = conn.execute(_statement)
    with native_result_scope("hold_submission", "lock_input_snapshot"):
        _native_result.scalar_one()
    return None


CAPTURE_CUT_CONTRACT_DIGEST = "4b8918c1b38115cb65ceb704c6aca787e318ef1a877b7dbbcdd16e552ea8bf1d"


class _capture_cutRequest(OperationResult):
    run_id: Annotated[RunId, Field(ge=RunId(-9223372036854775808), le=RunId(9223372036854775807))]
    name: str
    final: bool = False


_capture_cut_function = func.ops.capture_cut(
    bindparam("run_id", type_=BigInteger()),
    bindparam("name", type_=Text()),
    bindparam("final", type_=Boolean()),
    type_=BigInteger(),
)
_capture_cut_statement = select(_capture_cut_function)


def prepare_capture_cut(
    *,
    run_id: RunId,
    name: str,
    final: bool = False,
    projection_context: PreparedRelease | None = None,
) -> Select[int]:
    _request = _capture_cutRequest(
        run_id=run_id,
        name=name,
        final=final,
    )
    if projection_context is not None:
        require_call_context(
            projection_context, "capture_cut", "capture_cut", CAPTURE_CUT_CONTRACT_DIGEST
        )
    return _capture_cut_statement.params(
        **{
            "run_id": _request.run_id,
            "name": _request.name,
            "final": _request.final,
        }
    )


_capture_cut_adapter = TypeAdapter(CutId)


def materialize_capture_cut(row: tuple[int]) -> CutId:
    with native_result_scope("capture_cut", "capture_cut", "cut_id"):
        checked = _capture_cut_adapter.validate_python(row[0], strict=True)
        return checked


def capture_cut(
    conn: Connection,
    *,
    run_id: RunId,
    name: str,
    final: bool = False,
    projection_context: PreparedRelease | None = None,
) -> CutId:
    _statement = prepare_capture_cut(
        run_id=run_id,
        name=name,
        final=final,
        projection_context=projection_context,
    )
    _native_result = conn.execute(_statement)
    with native_result_scope("capture_cut", "capture_cut"):
        row = _native_result.one()
        return materialize_capture_cut(row)


START_SOURCE_RUN_CONTRACT_DIGEST = (
    "927770866e031c7cce77139dc258868611d1959016a3708a9f9c8d9bfd3a7594"
)


class _start_source_runRequest(OperationResult):
    run_id: Annotated[RunId, Field(ge=RunId(-9223372036854775808), le=RunId(9223372036854775807))]


_start_source_run_function = func.ops.start_source_run(
    bindparam("run_id", type_=BigInteger()),
    type_=BigInteger(),
)
_start_source_run_statement = select(_start_source_run_function)


def prepare_start_source_run(
    *,
    run_id: RunId,
    projection_context: PreparedRelease | None = None,
) -> Select[int]:
    _request = _start_source_runRequest(
        run_id=run_id,
    )
    if projection_context is not None:
        require_call_context(
            projection_context,
            "execute_source",
            "start_source_run",
            START_SOURCE_RUN_CONTRACT_DIGEST,
        )
    return _start_source_run_statement.params(
        **{
            "run_id": _request.run_id,
        }
    )


_start_source_run_adapter = TypeAdapter(RunId)


def materialize_start_source_run(row: tuple[int]) -> RunId:
    with native_result_scope("execute_source", "start_source_run", "run_id"):
        checked = _start_source_run_adapter.validate_python(row[0], strict=True)
        return checked


def start_source_run(
    conn: Connection,
    *,
    run_id: RunId,
    projection_context: PreparedRelease | None = None,
) -> RunId:
    _statement = prepare_start_source_run(
        run_id=run_id,
        projection_context=projection_context,
    )
    _native_result = conn.execute(_statement)
    with native_result_scope("execute_source", "start_source_run"):
        row = _native_result.one()
        return materialize_start_source_run(row)


END_SOURCE_RUN_CONTRACT_DIGEST = "778dff1e6b7ce7d6b045c4461882a852d80508c6cd1cf74b3b91dfe7a97bcf4d"


class _end_source_runRequest(OperationResult):
    run_id: Annotated[RunId, Field(ge=RunId(-9223372036854775808), le=RunId(9223372036854775807))]
    failure: JsonValue | None = None


_end_source_run_function = func.ops.end_source_run(
    bindparam("run_id", type_=BigInteger()),
    bindparam("failure", type_=JSONB(none_as_null=True)),
    type_=BigInteger(),
)
_end_source_run_statement = select(_end_source_run_function)


def prepare_end_source_run(
    *,
    run_id: RunId,
    failure: JsonValue | None = None,
    projection_context: PreparedRelease | None = None,
) -> Select[int]:
    _request = _end_source_runRequest(
        run_id=run_id,
        failure=failure,
    )
    if projection_context is not None:
        require_call_context(
            projection_context, "end_run", "end_source_run", END_SOURCE_RUN_CONTRACT_DIGEST
        )
    return _end_source_run_statement.params(
        **{
            "run_id": _request.run_id,
            "failure": _request.failure,
        }
    )


_end_source_run_adapter = TypeAdapter(int)


def materialize_end_source_run(row: tuple[int]) -> int:
    with native_result_scope("end_run", "end_source_run", "affected_tasks"):
        checked = _end_source_run_adapter.validate_python(row[0], strict=True)
        return checked


def end_source_run(
    conn: Connection,
    *,
    run_id: RunId,
    failure: JsonValue | None = None,
    projection_context: PreparedRelease | None = None,
) -> int:
    _statement = prepare_end_source_run(
        run_id=run_id,
        failure=failure,
        projection_context=projection_context,
    )
    _native_result = conn.execute(_statement)
    with native_result_scope("end_run", "end_source_run"):
        row = _native_result.one()
        return materialize_end_source_run(row)


RETAIN_SOURCE_ARTIFACT_CONTRACT_DIGEST = (
    "9ae9ab77bff3a4cbfd15ad512aab0e198d6f7a5d82a57629420096ed2183601e"
)


class _retain_source_artifactRequest(OperationResult):
    document_id: Annotated[
        DocumentId, Field(ge=DocumentId(-9223372036854775808), le=DocumentId(9223372036854775807))
    ]
    original: bytes


_retain_source_artifact_function = func.ops.retain_source_artifact(
    bindparam("document_id", type_=BigInteger()),
    bindparam("original", type_=BYTEA()),
    type_=Text(),
)
_retain_source_artifact_statement = select(_retain_source_artifact_function)


def prepare_retain_source_artifact(
    *,
    document_id: DocumentId,
    original: bytes,
    projection_context: PreparedRelease | None = None,
) -> Select[str]:
    _request = _retain_source_artifactRequest(
        document_id=document_id,
        original=original,
    )
    if projection_context is not None:
        require_call_context(
            projection_context,
            "register_document",
            "retain_source_artifact",
            RETAIN_SOURCE_ARTIFACT_CONTRACT_DIGEST,
        )
    return _retain_source_artifact_statement.params(
        **{
            "document_id": _request.document_id,
            "original": _request.original,
        }
    )


_retain_source_artifact_adapter = TypeAdapter(str)


def materialize_retain_source_artifact(row: tuple[str]) -> str:
    with native_result_scope("register_document", "retain_source_artifact", "digest"):
        checked = _retain_source_artifact_adapter.validate_python(row[0], strict=True)
        return checked


def retain_source_artifact(
    conn: Connection,
    *,
    document_id: DocumentId,
    original: bytes,
    projection_context: PreparedRelease | None = None,
) -> str:
    _statement = prepare_retain_source_artifact(
        document_id=document_id,
        original=original,
        projection_context=projection_context,
    )
    _native_result = conn.execute(_statement)
    with native_result_scope("register_document", "retain_source_artifact"):
        row = _native_result.one()
        return materialize_retain_source_artifact(row)


DOCUMENT_REGISTRATION_CONTRACT_DIGEST = (
    "fa237544d5a6807a7e5bd0db45342f0e9c766d466701e64369849040880b80eb"
)


class RegisteredDocument(NativeRowResult):
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


class _document_registrationRequest(OperationResult):
    project_id: ProjectId
    key: str
    source_uri: str
    content_hash: str
    original_path: str
    mime: str
    title: str | None
    meta: JsonValue


def prepare_document_registration(
    *,
    project_id: ProjectId,
    key: str,
    source_uri: str,
    content_hash: str,
    original_path: str,
    mime: str,
    title: str | None,
    meta: JsonValue,
    projection_context: PreparedRelease | None = None,
) -> _document_registrationRequest:
    _request = _document_registrationRequest(
        project_id=project_id,
        key=key,
        source_uri=source_uri,
        content_hash=content_hash,
        original_path=original_path,
        mime=mime,
        title=title,
        meta=meta,
    )
    if projection_context is not None:
        require_call_context(
            projection_context,
            "register_document",
            "document_registration",
            DOCUMENT_REGISTRATION_CONTRACT_DIGEST,
        )
    return _request


class DocumentRegistrationKbDocumentValues(TypedDict):
    project_id: ProjectId
    key: str
    source_uri: str
    content_hash: str
    original_path: str
    mime: str
    title: str | None
    meta: JsonValue


def values_document_registration_kb_document(
    request: _document_registrationRequest,
) -> DocumentRegistrationKbDocumentValues:
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


class DocumentRegistrationKbDocumentValuesExpected(TypedDict):
    project_id: ProjectId
    key: str
    source_uri: str
    content_hash: str
    original_path: str
    mime: str
    title: str | None
    meta: JsonValue


def expected_document_registration_kb_document(
    request: _document_registrationRequest,
) -> DocumentRegistrationKbDocumentValuesExpected:
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


class _document_registration_kb_documentColumns(TypedColumns):
    id: Named[int]
    project_id: Named[str]
    key: Named[str]
    source_uri: Named[str]
    content_hash: Named[str]
    original_path: Named[str]
    mime: Named[str]
    title: Named[str | None]
    meta: Named[JsonValue]


class _document_registration_kb_documentColumnsProtocol(Protocol):
    id: Column[int]
    project_id: Column[str]
    key: Column[str]
    source_uri: Column[str]
    content_hash: Column[str]
    original_path: Column[str]
    mime: Column[str]
    title: Column[str | None]
    meta: Column[JsonValue]


_document_registration_kb_document = _core_table("kb.document").with_cols(
    _document_registration_kb_documentColumns
)
_document_registration_kb_document_columns = cast(
    _document_registration_kb_documentColumnsProtocol, _document_registration_kb_document.c
)

projection_document_registration: tuple[
    ColumnElement[int],
    ColumnElement[str],
    ColumnElement[str],
    ColumnElement[str],
    ColumnElement[str],
    ColumnElement[str],
    ColumnElement[str],
    ColumnElement[str | None],
    ColumnElement[str],
] = (
    _document_registration_kb_document_columns.id.label("id"),
    _document_registration_kb_document_columns.project_id.label("project_id"),
    _document_registration_kb_document_columns.key.label("key"),
    _document_registration_kb_document_columns.source_uri.label("source_uri"),
    _document_registration_kb_document_columns.content_hash.label("content_hash"),
    _document_registration_kb_document_columns.original_path.label("original_path"),
    _document_registration_kb_document_columns.mime.label("mime"),
    _document_registration_kb_document_columns.title.label("title"),
    _document_registration_kb_document_columns.meta.cast(Text()).label("meta"),
)


def materialize_document_registration(
    row: tuple[int, str, str, str, str, str, str, str | None, str],
) -> RegisteredDocument:
    with native_result_scope("register_document", "RegisteredDocument"):
        return RegisteredDocument(
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


def collect_document_registration(
    result: Result[int, str, str, str, str, str, str, str | None, str],
) -> RegisteredDocument:
    with native_result_scope("register_document", "RegisteredDocument"):
        return materialize_document_registration(result.one())


ORIGINAL_DESCRIPTOR_CONTRACT_DIGEST = (
    "275132fd5612e78c7cd9a90b24a2b74811e56dfaad0f4371667799dbf84950b1"
)


class OriginalDescriptor(NativeRowResult):
    content_hash: str
    original_path: str


class _original_descriptorRequest(OperationResult):
    id: Annotated[
        DocumentId, Field(ge=DocumentId(-9223372036854775808), le=DocumentId(9223372036854775807))
    ]


def prepare_original_descriptor(
    *,
    id: DocumentId,
    projection_context: PreparedRelease | None = None,
) -> _original_descriptorRequest:
    _request = _original_descriptorRequest(
        id=id,
    )
    if projection_context is not None:
        require_call_context(
            projection_context,
            "read_original",
            "original_descriptor",
            ORIGINAL_DESCRIPTOR_CONTRACT_DIGEST,
        )
    return _request


class OriginalDescriptorKbDocumentValues(TypedDict):
    id: DocumentId


def values_original_descriptor_kb_document(
    request: _original_descriptorRequest,
) -> OriginalDescriptorKbDocumentValues:
    return {
        "id": request.id,
    }


class OriginalDescriptorKbDocumentValuesExpected(TypedDict):
    id: DocumentId


def expected_original_descriptor_kb_document(
    request: _original_descriptorRequest,
) -> OriginalDescriptorKbDocumentValuesExpected:
    return {
        "id": request.id,
    }


class _original_descriptor_kb_documentColumns(TypedColumns):
    content_hash: Named[str]
    original_path: Named[str]


class _original_descriptor_kb_documentColumnsProtocol(Protocol):
    content_hash: Column[str]
    original_path: Column[str]


_original_descriptor_kb_document = _core_table("kb.document").with_cols(
    _original_descriptor_kb_documentColumns
)
_original_descriptor_kb_document_columns = cast(
    _original_descriptor_kb_documentColumnsProtocol, _original_descriptor_kb_document.c
)

projection_original_descriptor: tuple[ColumnElement[str], ColumnElement[str]] = (
    _original_descriptor_kb_document_columns.content_hash.label("content_hash"),
    _original_descriptor_kb_document_columns.original_path.label("original_path"),
)


def materialize_original_descriptor(row: tuple[str, str]) -> OriginalDescriptor:
    with native_result_scope("read_original", "OriginalDescriptor"):
        return OriginalDescriptor(
            content_hash=row[0],
            original_path=row[1],
        )


def collect_original_descriptor(result: Result[str, str]) -> OriginalDescriptor | None:
    with native_result_scope("read_original", "OriginalDescriptor"):
        row = result.one_or_none()
        return None if row is None else materialize_original_descriptor(row)


ORIGINAL_ARTIFACT_CONTRACT_DIGEST = (
    "146cf1f69c49db52f2b5f6813373442b487e01f5dff857119ba5f9850827b6c9"
)


class _original_artifactRequest(OperationResult):
    artifact_digest: str


def prepare_original_artifact(
    *,
    artifact_digest: str,
    projection_context: PreparedRelease | None = None,
) -> _original_artifactRequest:
    _request = _original_artifactRequest(
        artifact_digest=artifact_digest,
    )
    if projection_context is not None:
        require_call_context(
            projection_context,
            "read_original",
            "original_artifact",
            ORIGINAL_ARTIFACT_CONTRACT_DIGEST,
        )
    return _request


class OriginalArtifactKbSourceArtifactValues(TypedDict):
    artifact_digest: str


def values_original_artifact_kb_source_artifact(
    request: _original_artifactRequest,
) -> OriginalArtifactKbSourceArtifactValues:
    return {
        "artifact_digest": request.artifact_digest,
    }


class OriginalArtifactKbSourceArtifactValuesExpected(TypedDict):
    artifact_digest: str


def expected_original_artifact_kb_source_artifact(
    request: _original_artifactRequest,
) -> OriginalArtifactKbSourceArtifactValuesExpected:
    return {
        "artifact_digest": request.artifact_digest,
    }


class _original_artifact_kb_source_artifactColumns(TypedColumns):
    content: Named[bytes]


class _original_artifact_kb_source_artifactColumnsProtocol(Protocol):
    content: Column[bytes]


_original_artifact_kb_source_artifact = _core_table("kb.source_artifact").with_cols(
    _original_artifact_kb_source_artifactColumns
)
_original_artifact_kb_source_artifact_columns = cast(
    _original_artifact_kb_source_artifactColumnsProtocol, _original_artifact_kb_source_artifact.c
)

projection_original_artifact: tuple[ColumnElement[bytes]] = (
    _original_artifact_kb_source_artifact_columns.content.label("content"),
)

_original_artifact_adapter = TypeAdapter(bytes)


def materialize_original_artifact(row: tuple[bytes]) -> bytes:
    with native_result_scope("read_original", "bytes"):
        return _original_artifact_adapter.validate_python(row[0], strict=True)


def collect_original_artifact(result: Result[bytes]) -> bytes | None:
    with native_result_scope("read_original", "bytes"):
        row = result.one_or_none()
        return None if row is None else materialize_original_artifact(row)


BEGIN_EVALUATION_CONTRACT_DIGEST = (
    "585671606ccc33ed88a5c352275c9d3b57859218eb9478f29a33dacd6c9e1479"
)


class _begin_evaluationRequest(OperationResult):
    cut_id: Annotated[CutId, Field(ge=CutId(-9223372036854775808), le=CutId(9223372036854775807))]
    output_realization_id: RealizationId


_begin_evaluation_function = func.data.begin_evaluation(
    bindparam("cut_id", type_=BigInteger()),
    bindparam("output_realization_id", type_=Text()),
)
_begin_evaluation_statement = select(_begin_evaluation_function)


def prepare_begin_evaluation(
    *,
    cut_id: CutId,
    output_realization_id: RealizationId,
    projection_context: PreparedRelease | None = None,
) -> Select[None]:
    _request = _begin_evaluationRequest(
        cut_id=cut_id,
        output_realization_id=output_realization_id,
    )
    if projection_context is not None:
        require_call_context(
            projection_context, "evaluate", "begin_evaluation", BEGIN_EVALUATION_CONTRACT_DIGEST
        )
    return _begin_evaluation_statement.params(
        **{
            "cut_id": _request.cut_id,
            "output_realization_id": _request.output_realization_id,
        }
    )


def begin_evaluation(
    conn: Connection,
    *,
    cut_id: CutId,
    output_realization_id: RealizationId,
    projection_context: PreparedRelease | None = None,
) -> None:
    _statement = prepare_begin_evaluation(
        cut_id=cut_id,
        output_realization_id=output_realization_id,
        projection_context=projection_context,
    )
    _native_result = conn.execute(_statement)
    with native_result_scope("evaluate", "begin_evaluation"):
        _native_result.scalar_one()
    return None


END_STAGE_CONTRACT_DIGEST = "be2ed48ff0b1ba51031151e2a7e00748e40fdcc637730014c51cbfa9b9307c8f"


class _end_stageRequest(OperationResult):
    pass


_end_stage_function = func.data.end_stage()
_end_stage_statement = select(_end_stage_function)


def prepare_end_stage(
    *,
    projection_context: PreparedRelease | None = None,
) -> Select[None]:
    _request = _end_stageRequest()
    if projection_context is not None:
        require_call_context(projection_context, "evaluate", "end_stage", END_STAGE_CONTRACT_DIGEST)
    return _end_stage_statement.params(**{})


def end_stage(
    conn: Connection,
    *,
    projection_context: PreparedRelease | None = None,
) -> None:
    _statement = prepare_end_stage(
        projection_context=projection_context,
    )
    _native_result = conn.execute(_statement)
    with native_result_scope("evaluate", "end_stage"):
        _native_result.scalar_one()
    return None


FINISH_EVALUATION_CONTRACT_DIGEST = (
    "c63b09992034f00d018aee2918bdd079d74a1b60fbd69cd156a83f98ef00f9ce"
)


class _finish_evaluationRequest(OperationResult):
    cut_id: Annotated[CutId, Field(ge=CutId(-9223372036854775808), le=CutId(9223372036854775807))]
    output_realization_id: RealizationId
    batch_id: str


_finish_evaluation_function = func.data.finish_evaluation(
    bindparam("cut_id", type_=BigInteger()),
    bindparam("output_realization_id", type_=Text()),
    bindparam("batch_id", type_=Text()),
)
_finish_evaluation_statement = select(_finish_evaluation_function)


def prepare_finish_evaluation(
    *,
    cut_id: CutId,
    output_realization_id: RealizationId,
    batch_id: str,
    projection_context: PreparedRelease | None = None,
) -> Select[None]:
    _request = _finish_evaluationRequest(
        cut_id=cut_id,
        output_realization_id=output_realization_id,
        batch_id=batch_id,
    )
    if projection_context is not None:
        require_call_context(
            projection_context, "evaluate", "finish_evaluation", FINISH_EVALUATION_CONTRACT_DIGEST
        )
    return _finish_evaluation_statement.params(
        **{
            "cut_id": _request.cut_id,
            "output_realization_id": _request.output_realization_id,
            "batch_id": _request.batch_id,
        }
    )


def finish_evaluation(
    conn: Connection,
    *,
    cut_id: CutId,
    output_realization_id: RealizationId,
    batch_id: str,
    projection_context: PreparedRelease | None = None,
) -> None:
    _statement = prepare_finish_evaluation(
        cut_id=cut_id,
        output_realization_id=output_realization_id,
        batch_id=batch_id,
        projection_context=projection_context,
    )
    _native_result = conn.execute(_statement)
    with native_result_scope("evaluate", "finish_evaluation"):
        _native_result.scalar_one()
    return None


LOCK_FINALIZATION_RUN_CONTRACT_DIGEST = (
    "0365b8c598a91840084912fac61766772f68ada355be93391ae5cf0286271fd1"
)


class LockedFinalizationRun(NativeRowResult):
    __json_fields__ = ("options",)
    id: int
    project_id: str
    release_id: str
    runtime_id: str | None
    input_realization_id: str
    input_revision: int
    dependency_digest: str
    dependencies: bytes
    kind: str
    phase: int
    options: str
    guideline: str
    status: str
    code_commit: str
    result_realization_id: str | None
    sealed: bool


class _lock_finalization_runRequest(OperationResult):
    run_id: Annotated[RunId, Field(ge=RunId(-9223372036854775808), le=RunId(9223372036854775807))]


_lock_finalization_run_function = func.ops.lock_finalization_run(
    bindparam("run_id", type_=BigInteger()),
).table_valued(
    column("id", BigInteger()),
    column("project_id", Text()),
    column("release_id", Text()),
    column("runtime_id", Text()),
    column("input_realization_id", Text()),
    column("input_revision", BigInteger()),
    column("dependency_digest", Text()),
    column("dependencies", BYTEA()),
    column("kind", Text()),
    column("phase", BigInteger()),
    column("options", JSONB()),
    column("guideline", Text()),
    column("status", Text()),
    column("code_commit", Text()),
    column("result_realization_id", Text()),
    column("sealed", Boolean()),
)


class _lock_finalization_runColumns(Protocol):
    id: Column[int]
    project_id: Column[str]
    release_id: Column[str]
    runtime_id: Column[str | None]
    input_realization_id: Column[str]
    input_revision: Column[int]
    dependency_digest: Column[str]
    dependencies: Column[bytes]
    kind: Column[str]
    phase: Column[int]
    options: Column[JsonValue]
    guideline: Column[str]
    status: Column[str]
    code_commit: Column[str]
    result_realization_id: Column[str | None]
    sealed: Column[bool]


_lock_finalization_run_columns = cast(
    _lock_finalization_runColumns, _lock_finalization_run_function.c
)
_lock_finalization_run_statement = select(
    _lock_finalization_run_columns.id,
    _lock_finalization_run_columns.project_id,
    _lock_finalization_run_columns.release_id,
    _lock_finalization_run_columns.runtime_id,
    _lock_finalization_run_columns.input_realization_id,
    _lock_finalization_run_columns.input_revision,
    _lock_finalization_run_columns.dependency_digest,
    _lock_finalization_run_columns.dependencies,
    _lock_finalization_run_columns.kind,
    _lock_finalization_run_columns.phase,
    _lock_finalization_run_columns.options.cast(Text()).label("options"),
    _lock_finalization_run_columns.guideline,
    _lock_finalization_run_columns.status,
    _lock_finalization_run_columns.code_commit,
    _lock_finalization_run_columns.result_realization_id,
    _lock_finalization_run_columns.sealed,
)


def _lock_finalization_run_result(
    row: tuple[
        int,
        str,
        str,
        str | None,
        str,
        int,
        str,
        bytes,
        str,
        int,
        str,
        str,
        str,
        str,
        str | None,
        bool,
    ],
) -> LockedFinalizationRun:
    with native_result_scope("evaluate", "LockedFinalizationRun"):
        return LockedFinalizationRun(
            id=row[0],
            project_id=row[1],
            release_id=row[2],
            runtime_id=row[3],
            input_realization_id=row[4],
            input_revision=row[5],
            dependency_digest=row[6],
            dependencies=row[7],
            kind=row[8],
            phase=row[9],
            options=row[10],
            guideline=row[11],
            status=row[12],
            code_commit=row[13],
            result_realization_id=row[14],
            sealed=row[15],
        )


def prepare_lock_finalization_run(
    *,
    run_id: RunId,
    projection_context: PreparedRelease | None = None,
) -> Select[
    int, str, str, str | None, str, int, str, bytes, str, int, str, str, str, str, str | None, bool
]:
    _request = _lock_finalization_runRequest(
        run_id=run_id,
    )
    if projection_context is not None:
        require_call_context(
            projection_context,
            "evaluate",
            "lock_finalization_run",
            LOCK_FINALIZATION_RUN_CONTRACT_DIGEST,
        )
    return _lock_finalization_run_statement.params(
        **{
            "run_id": _request.run_id,
        }
    )


materialize_lock_finalization_run = _lock_finalization_run_result


def lock_finalization_run(
    conn: Connection,
    *,
    run_id: RunId,
    projection_context: PreparedRelease | None = None,
) -> LockedFinalizationRun:
    _statement = prepare_lock_finalization_run(
        run_id=run_id,
        projection_context=projection_context,
    )
    _native_result = conn.execute(_statement)
    with native_result_scope("evaluate", "LockedFinalizationRun"):
        return _lock_finalization_run_result(_native_result.one())


BEGIN_INFERENCE_WORKSPACE_CONTRACT_DIGEST = (
    "10a239a23e3c75414da2bdf2eabe2a7120266135763cc23614d43190620546c5"
)


class _begin_inference_workspaceRequest(OperationResult):
    release_id: ReleaseId
    realization_id: RealizationId
    revision: Annotated[int, Field(ge=-9223372036854775808, le=9223372036854775807)]
    snapshot: str


_begin_inference_workspace_function = func.data.begin_inference_workspace(
    bindparam("release_id", type_=Text()),
    bindparam("realization_id", type_=Text()),
    bindparam("revision", type_=BigInteger()),
    bindparam("snapshot", type_=Text()),
)
_begin_inference_workspace_statement = select(_begin_inference_workspace_function)


def prepare_begin_inference_workspace(
    *,
    release_id: ReleaseId,
    realization_id: RealizationId,
    revision: int,
    snapshot: str,
    projection_context: PreparedRelease | None = None,
) -> Select[None]:
    _request = _begin_inference_workspaceRequest(
        release_id=release_id,
        realization_id=realization_id,
        revision=revision,
        snapshot=snapshot,
    )
    if projection_context is not None:
        require_call_context(
            projection_context,
            "derive",
            "begin_inference_workspace",
            BEGIN_INFERENCE_WORKSPACE_CONTRACT_DIGEST,
        )
    return _begin_inference_workspace_statement.params(
        **{
            "release_id": _request.release_id,
            "realization_id": _request.realization_id,
            "revision": _request.revision,
            "snapshot": _request.snapshot,
        }
    )


def begin_inference_workspace(
    conn: Connection,
    *,
    release_id: ReleaseId,
    realization_id: RealizationId,
    revision: int,
    snapshot: str,
    projection_context: PreparedRelease | None = None,
) -> None:
    _statement = prepare_begin_inference_workspace(
        release_id=release_id,
        realization_id=realization_id,
        revision=revision,
        snapshot=snapshot,
        projection_context=projection_context,
    )
    _native_result = conn.execute(_statement)
    with native_result_scope("derive", "begin_inference_workspace"):
        _native_result.scalar_one()
    return None


END_INFERENCE_WORKSPACE_CONTRACT_DIGEST = (
    "71ce468d972facfb76e7c8c75ea2dd475f1c30a989db18f87f4399155389553a"
)


class _end_inference_workspaceRequest(OperationResult):
    release_id: ReleaseId
    realization_id: RealizationId
    revision: Annotated[int, Field(ge=-9223372036854775808, le=9223372036854775807)]
    snapshot: str


_end_inference_workspace_function = func.data.end_inference_workspace(
    bindparam("release_id", type_=Text()),
    bindparam("realization_id", type_=Text()),
    bindparam("revision", type_=BigInteger()),
    bindparam("snapshot", type_=Text()),
)
_end_inference_workspace_statement = select(_end_inference_workspace_function)


def prepare_end_inference_workspace(
    *,
    release_id: ReleaseId,
    realization_id: RealizationId,
    revision: int,
    snapshot: str,
    projection_context: PreparedRelease | None = None,
) -> Select[None]:
    _request = _end_inference_workspaceRequest(
        release_id=release_id,
        realization_id=realization_id,
        revision=revision,
        snapshot=snapshot,
    )
    if projection_context is not None:
        require_call_context(
            projection_context,
            "derive",
            "end_inference_workspace",
            END_INFERENCE_WORKSPACE_CONTRACT_DIGEST,
        )
    return _end_inference_workspace_statement.params(
        **{
            "release_id": _request.release_id,
            "realization_id": _request.realization_id,
            "revision": _request.revision,
            "snapshot": _request.snapshot,
        }
    )


def end_inference_workspace(
    conn: Connection,
    *,
    release_id: ReleaseId,
    realization_id: RealizationId,
    revision: int,
    snapshot: str,
    projection_context: PreparedRelease | None = None,
) -> None:
    _statement = prepare_end_inference_workspace(
        release_id=release_id,
        realization_id=realization_id,
        revision=revision,
        snapshot=snapshot,
        projection_context=projection_context,
    )
    _native_result = conn.execute(_statement)
    with native_result_scope("derive", "end_inference_workspace"):
        _native_result.scalar_one()
    return None


BEGIN_STAGE_CONTRACT_DIGEST = "88805f7746ca9d88171157e2677a99bc59c3a25c1726e5afb223eed8bd60dd37"


class _begin_stageRequest(OperationResult):
    pass


_begin_stage_function = func.data.begin_stage()
_begin_stage_statement = select(_begin_stage_function)


def prepare_begin_stage(
    *,
    projection_context: PreparedRelease | None = None,
) -> Select[None]:
    _request = _begin_stageRequest()
    if projection_context is not None:
        require_call_context(
            projection_context, "publish", "begin_stage", BEGIN_STAGE_CONTRACT_DIGEST
        )
    return _begin_stage_statement.params(**{})


def begin_stage(
    conn: Connection,
    *,
    projection_context: PreparedRelease | None = None,
) -> None:
    _statement = prepare_begin_stage(
        projection_context=projection_context,
    )
    _native_result = conn.execute(_statement)
    with native_result_scope("publish", "begin_stage"):
        _native_result.scalar_one()
    return None


PUBLISH_BATCH_CONTRACT_DIGEST = "8f27a1d3b4ffed08287c4c3ac06d7e7ce60d3f0e9997daf666d13f1e1acb09ec"


class _publish_batchRequest(OperationResult):
    release_id: ReleaseId
    realization_id: RealizationId
    batch_id: str
    content: bytes


_publish_batch_function = func.data.publish_batch(
    bindparam("release_id", type_=Text()),
    bindparam("realization_id", type_=Text()),
    bindparam("batch_id", type_=Text()),
    bindparam("content", type_=BYTEA()),
    type_=BigInteger(),
)
_publish_batch_statement = select(_publish_batch_function)


def prepare_publish_batch(
    *,
    release_id: ReleaseId,
    realization_id: RealizationId,
    batch_id: str,
    content: bytes,
    projection_context: PreparedRelease | None = None,
) -> Select[int]:
    _request = _publish_batchRequest(
        release_id=release_id,
        realization_id=realization_id,
        batch_id=batch_id,
        content=content,
    )
    if projection_context is not None:
        require_call_context(
            projection_context, "publish", "publish_batch", PUBLISH_BATCH_CONTRACT_DIGEST
        )
    return _publish_batch_statement.params(
        **{
            "release_id": _request.release_id,
            "realization_id": _request.realization_id,
            "batch_id": _request.batch_id,
            "content": _request.content,
        }
    )


_publish_batch_adapter = TypeAdapter(int)


def materialize_publish_batch(row: tuple[int]) -> int:
    with native_result_scope("publish", "publish_batch", "data_revision"):
        checked = _publish_batch_adapter.validate_python(row[0], strict=True)
        return checked


def publish_batch(
    conn: Connection,
    *,
    release_id: ReleaseId,
    realization_id: RealizationId,
    batch_id: str,
    content: bytes,
    projection_context: PreparedRelease | None = None,
) -> int:
    _statement = prepare_publish_batch(
        release_id=release_id,
        realization_id=realization_id,
        batch_id=batch_id,
        content=content,
        projection_context=projection_context,
    )
    _native_result = conn.execute(_statement)
    with native_result_scope("publish", "publish_batch"):
        row = _native_result.one()
        return materialize_publish_batch(row)


REQUIRE_RUNTIME_PRINCIPAL_CONTRACT_DIGEST = (
    "bb1dbd69adb2c9ef8914e2a3cafa1834b59785902d05cd0a2ec35b82aa9e8e67"
)


class _require_runtime_principalRequest(OperationResult):
    purpose: NativeAdmissionParametersPurpose


_require_runtime_principal_function = func.data.require_runtime_principal(
    bindparam("purpose", type_=Text()),
)
_require_runtime_principal_statement = select(_require_runtime_principal_function)


def prepare_require_runtime_principal(
    *,
    purpose: NativeAdmissionParametersPurpose,
    projection_context: PreparedRelease | None = None,
) -> Select[None]:
    _request = _require_runtime_principalRequest(
        purpose=purpose,
    )
    if projection_context is not None:
        require_call_context(
            projection_context,
            "admit",
            "require_runtime_principal",
            REQUIRE_RUNTIME_PRINCIPAL_CONTRACT_DIGEST,
        )
    return _require_runtime_principal_statement.params(
        **{
            "purpose": _request.purpose,
        }
    )


def require_runtime_principal(
    conn: Connection,
    *,
    purpose: NativeAdmissionParametersPurpose,
    projection_context: PreparedRelease | None = None,
) -> None:
    _statement = prepare_require_runtime_principal(
        purpose=purpose,
        projection_context=projection_context,
    )
    _native_result = conn.execute(_statement)
    with native_result_scope("admit", "require_runtime_principal"):
        _native_result.scalar_one()
    return None


REQUIRE_NATIVE_EXECUTION_RELEASE_CONTRACT_DIGEST = (
    "26f4126313712330b35b0c1d5466b53e4bff5db9c5148ad5f5c4143be14bef02"
)


class _require_native_execution_releaseRequest(OperationResult):
    release_id: ReleaseId


_require_native_execution_release_function = func.data.require_execution_release(
    bindparam("release_id", type_=Text()),
)
_require_native_execution_release_statement = select(_require_native_execution_release_function)


def prepare_require_native_execution_release(
    *,
    release_id: ReleaseId,
    projection_context: PreparedRelease | None = None,
) -> Select[None]:
    _request = _require_native_execution_releaseRequest(
        release_id=release_id,
    )
    if projection_context is not None:
        require_call_context(
            projection_context,
            "admit",
            "require_native_execution_release",
            REQUIRE_NATIVE_EXECUTION_RELEASE_CONTRACT_DIGEST,
        )
    return _require_native_execution_release_statement.params(
        **{
            "release_id": _request.release_id,
        }
    )


def require_native_execution_release(
    conn: Connection,
    *,
    release_id: ReleaseId,
    projection_context: PreparedRelease | None = None,
) -> None:
    _statement = prepare_require_native_execution_release(
        release_id=release_id,
        projection_context=projection_context,
    )
    _native_result = conn.execute(_statement)
    with native_result_scope("admit", "require_native_execution_release"):
        _native_result.scalar_one()
    return None


REQUIRE_EXECUTION_OPERATION_CONTRACT_DIGEST = (
    "278b1a9bf886da94f1073b9f8f1da259e5fea3cb230fa45fc36876d370821cd5"
)


class _require_execution_operationRequest(OperationResult):
    release_id: ReleaseId
    operation: str


_require_execution_operation_function = func.sem.require_execution_operation(
    bindparam("release_id", type_=Text()),
    bindparam("operation", type_=Text()),
)
_require_execution_operation_statement = select(_require_execution_operation_function)


def prepare_require_execution_operation(
    *,
    release_id: ReleaseId,
    operation: str,
    projection_context: PreparedRelease | None = None,
) -> Select[None]:
    _request = _require_execution_operationRequest(
        release_id=release_id,
        operation=operation,
    )
    if projection_context is not None:
        require_call_context(
            projection_context,
            "admit",
            "require_execution_operation",
            REQUIRE_EXECUTION_OPERATION_CONTRACT_DIGEST,
        )
    return _require_execution_operation_statement.params(
        **{
            "release_id": _request.release_id,
            "operation": _request.operation,
        }
    )


def require_execution_operation(
    conn: Connection,
    *,
    release_id: ReleaseId,
    operation: str,
    projection_context: PreparedRelease | None = None,
) -> None:
    _statement = prepare_require_execution_operation(
        release_id=release_id,
        operation=operation,
        projection_context=projection_context,
    )
    _native_result = conn.execute(_statement)
    with native_result_scope("admit", "require_execution_operation"):
        _native_result.scalar_one()
    return None


RECORD_SQL_ADMISSION_CONTRACT_DIGEST = (
    "587b6ae3221e62b88d4de2bde9f1c75aa81f01dc9beecbf51681d75b3c7a4284"
)


class _record_sql_admissionRequest(OperationResult):
    release_id: ReleaseId
    input_kind: str
    input_name: str
    physical_id: str
    content: bytes


_record_sql_admission_function = func.sem.record_sql_admission(
    bindparam("release_id", type_=Text()),
    bindparam("input_kind", type_=Text()),
    bindparam("input_name", type_=Text()),
    bindparam("physical_id", type_=Text()),
    bindparam("content", type_=BYTEA()),
)
_record_sql_admission_statement = select(_record_sql_admission_function)


def prepare_record_sql_admission(
    *,
    release_id: ReleaseId,
    input_kind: str,
    input_name: str,
    physical_id: str,
    content: bytes,
    projection_context: PreparedRelease | None = None,
) -> Select[None]:
    _request = _record_sql_admissionRequest(
        release_id=release_id,
        input_kind=input_kind,
        input_name=input_name,
        physical_id=physical_id,
        content=content,
    )
    if projection_context is not None:
        require_call_context(
            projection_context,
            "admit",
            "record_sql_admission",
            RECORD_SQL_ADMISSION_CONTRACT_DIGEST,
        )
    return _record_sql_admission_statement.params(
        **{
            "release_id": _request.release_id,
            "input_kind": _request.input_kind,
            "input_name": _request.input_name,
            "physical_id": _request.physical_id,
            "content": _request.content,
        }
    )


def record_sql_admission(
    conn: Connection,
    *,
    release_id: ReleaseId,
    input_kind: str,
    input_name: str,
    physical_id: str,
    content: bytes,
    projection_context: PreparedRelease | None = None,
) -> None:
    _statement = prepare_record_sql_admission(
        release_id=release_id,
        input_kind=input_kind,
        input_name=input_name,
        physical_id=physical_id,
        content=content,
        projection_context=projection_context,
    )
    _native_result = conn.execute(_statement)
    with native_result_scope("admit", "record_sql_admission"):
        _native_result.scalar_one()
    return None


PUBLISH_DERIVED_BATCH_CONTRACT_DIGEST = (
    "850a7db63cf34efa50703f619f8701495a7e63f14826eb5bec642b190b9d24a6"
)


class _publish_derived_batchRequest(OperationResult):
    release_id: ReleaseId
    realization_id: RealizationId
    batch_id: str
    content: bytes
    source_release_id: ReleaseId
    source_realization_id: RealizationId
    source_revision: Annotated[int, Field(ge=-9223372036854775808, le=9223372036854775807)]
    source_capture_id: str
    operation: str
    projection: str
    contract_id: str | None
    cut_id: (
        Annotated[CutId, Field(ge=CutId(-9223372036854775808), le=CutId(9223372036854775807))]
        | None
    )
    profile_digest: str | None


_publish_derived_batch_function = func.data.publish_derived_batch_v2(
    bindparam("release_id", type_=Text()),
    bindparam("realization_id", type_=Text()),
    bindparam("batch_id", type_=Text()),
    bindparam("content", type_=BYTEA()),
    bindparam("source_release_id", type_=Text()),
    bindparam("source_realization_id", type_=Text()),
    bindparam("source_revision", type_=BigInteger()),
    bindparam("source_capture_id", type_=Text()),
    bindparam("operation", type_=Text()),
    bindparam("projection", type_=Text()),
    bindparam("contract_id", type_=Text()),
    bindparam("cut_id", type_=BigInteger()),
    bindparam("profile_digest", type_=Text()),
    type_=BigInteger(),
)
_publish_derived_batch_statement = select(_publish_derived_batch_function)


def prepare_publish_derived_batch(
    *,
    release_id: ReleaseId,
    realization_id: RealizationId,
    batch_id: str,
    content: bytes,
    source_release_id: ReleaseId,
    source_realization_id: RealizationId,
    source_revision: int,
    source_capture_id: str,
    operation: str,
    projection: str,
    contract_id: str | None,
    cut_id: CutId | None,
    profile_digest: str | None,
    projection_context: PreparedRelease | None = None,
) -> Select[int]:
    _request = _publish_derived_batchRequest(
        release_id=release_id,
        realization_id=realization_id,
        batch_id=batch_id,
        content=content,
        source_release_id=source_release_id,
        source_realization_id=source_realization_id,
        source_revision=source_revision,
        source_capture_id=source_capture_id,
        operation=operation,
        projection=projection,
        contract_id=contract_id,
        cut_id=cut_id,
        profile_digest=profile_digest,
    )
    if projection_context is not None:
        require_call_context(
            projection_context,
            "publish_arrow",
            "publish_derived_batch",
            PUBLISH_DERIVED_BATCH_CONTRACT_DIGEST,
        )
    return _publish_derived_batch_statement.params(
        **{
            "release_id": _request.release_id,
            "realization_id": _request.realization_id,
            "batch_id": _request.batch_id,
            "content": _request.content,
            "source_release_id": _request.source_release_id,
            "source_realization_id": _request.source_realization_id,
            "source_revision": _request.source_revision,
            "source_capture_id": _request.source_capture_id,
            "operation": _request.operation,
            "projection": _request.projection,
            "contract_id": _request.contract_id,
            "cut_id": _request.cut_id,
            "profile_digest": _request.profile_digest,
        }
    )


_publish_derived_batch_adapter = TypeAdapter(int)


def materialize_publish_derived_batch(row: tuple[int]) -> int:
    with native_result_scope("publish_arrow", "publish_derived_batch", "data_revision"):
        checked = _publish_derived_batch_adapter.validate_python(row[0], strict=True)
        return checked


def publish_derived_batch(
    conn: Connection,
    *,
    release_id: ReleaseId,
    realization_id: RealizationId,
    batch_id: str,
    content: bytes,
    source_release_id: ReleaseId,
    source_realization_id: RealizationId,
    source_revision: int,
    source_capture_id: str,
    operation: str,
    projection: str,
    contract_id: str | None,
    cut_id: CutId | None,
    profile_digest: str | None,
    projection_context: PreparedRelease | None = None,
) -> int:
    _statement = prepare_publish_derived_batch(
        release_id=release_id,
        realization_id=realization_id,
        batch_id=batch_id,
        content=content,
        source_release_id=source_release_id,
        source_realization_id=source_realization_id,
        source_revision=source_revision,
        source_capture_id=source_capture_id,
        operation=operation,
        projection=projection,
        contract_id=contract_id,
        cut_id=cut_id,
        profile_digest=profile_digest,
        projection_context=projection_context,
    )
    _native_result = conn.execute(_statement)
    with native_result_scope("publish_arrow", "publish_derived_batch"):
        row = _native_result.one()
        return materialize_publish_derived_batch(row)


RENEW_CLAIM_CONTRACT_DIGEST = "0877ce5f714e0465b44976c8fbf81dd3d2b0a34b7951c31a4814627cc7f587fb"


class _renew_claimRequest(OperationResult):
    task_id: Annotated[
        TaskId, Field(ge=TaskId(-9223372036854775808), le=TaskId(9223372036854775807))
    ]
    attempt: Annotated[
        TaskAttempt,
        Field(ge=TaskAttempt(-9223372036854775808), le=TaskAttempt(9223372036854775807)),
    ]
    holder: str


_renew_claim_function = func.ops.renew_claim(
    bindparam("task_id", type_=BigInteger()),
    bindparam("attempt", type_=BigInteger()),
    bindparam("holder", type_=Text()),
)
_renew_claim_statement = select(_renew_claim_function)


def prepare_renew_claim(
    *,
    task_id: TaskId,
    attempt: TaskAttempt,
    holder: str,
    projection_context: PreparedRelease | None = None,
) -> Select[None]:
    _request = _renew_claimRequest(
        task_id=task_id,
        attempt=attempt,
        holder=holder,
    )
    if projection_context is not None:
        require_call_context(
            projection_context, "renew_claim", "renew_claim", RENEW_CLAIM_CONTRACT_DIGEST
        )
    return _renew_claim_statement.params(
        **{
            "task_id": _request.task_id,
            "attempt": _request.attempt,
            "holder": _request.holder,
        }
    )


def renew_claim(
    conn: Connection,
    *,
    task_id: TaskId,
    attempt: TaskAttempt,
    holder: str,
    projection_context: PreparedRelease | None = None,
) -> None:
    _statement = prepare_renew_claim(
        task_id=task_id,
        attempt=attempt,
        holder=holder,
        projection_context=projection_context,
    )
    _native_result = conn.execute(_statement)
    with native_result_scope("renew_claim", "renew_claim"):
        _native_result.scalar_one()
    return None


RELEASE_CLAIM_CONTRACT_DIGEST = "cf7ab283a5aa023ac948715352b3ead6561eb939792979f234ba6851732e1d66"


@dataclass(frozen=True)
class ReleasedClaim:
    task_id: TaskId
    attempt: TaskAttempt
    reason: str


class _release_claimRequest(OperationResult):
    task_id: Annotated[
        TaskId, Field(ge=TaskId(-9223372036854775808), le=TaskId(9223372036854775807))
    ]
    attempt: Annotated[
        TaskAttempt,
        Field(ge=TaskAttempt(-9223372036854775808), le=TaskAttempt(9223372036854775807)),
    ]
    holder: str
    reason: str


_release_claim_function = func.ops.release_claim(
    bindparam("task_id", type_=BigInteger()),
    bindparam("attempt", type_=BigInteger()),
    bindparam("holder", type_=Text()),
    bindparam("reason", type_=Text()),
)
_release_claim_statement = select(_release_claim_function)


def prepare_release_claim(
    *,
    task_id: TaskId,
    attempt: TaskAttempt,
    holder: str,
    reason: str,
    projection_context: PreparedRelease | None = None,
) -> Select[None]:
    _request = _release_claimRequest(
        task_id=task_id,
        attempt=attempt,
        holder=holder,
        reason=reason,
    )
    if projection_context is not None:
        require_call_context(
            projection_context, "release_claim", "release_claim", RELEASE_CLAIM_CONTRACT_DIGEST
        )
    return _release_claim_statement.params(
        **{
            "task_id": _request.task_id,
            "attempt": _request.attempt,
            "holder": _request.holder,
            "reason": _request.reason,
        }
    )


def release_claim(
    conn: Connection,
    *,
    task_id: TaskId,
    attempt: TaskAttempt,
    holder: str,
    reason: str,
    projection_context: PreparedRelease | None = None,
) -> ReleasedClaim:
    _statement = prepare_release_claim(
        task_id=task_id,
        attempt=attempt,
        holder=holder,
        reason=reason,
        projection_context=projection_context,
    )
    _native_result = conn.execute(_statement)
    with native_result_scope("release_claim", "ReleasedClaim"):
        _native_result.scalar_one()
    return ReleasedClaim(
        task_id=task_id,
        attempt=attempt,
        reason=reason,
    )


SELECT_COMPLETED_RESULT_CONTRACT_DIGEST = (
    "bb5f5bd23930b19a429137acdacd6efdf225b2f39aa4b3802e836822bd545452"
)


class _select_completed_resultRequest(OperationResult):
    project_id: ProjectId
    run_id: Annotated[RunId, Field(ge=RunId(-9223372036854775808), le=RunId(9223372036854775807))]
    expected_generation: Annotated[int, Field(ge=-9223372036854775808, le=9223372036854775807)]


_select_completed_result_function = func.sem.select_completed_result(
    bindparam("project_id", type_=Text()),
    bindparam("run_id", type_=BigInteger()),
    bindparam("expected_generation", type_=BigInteger()),
    type_=BigInteger(),
)
_select_completed_result_statement = select(_select_completed_result_function)


def prepare_select_completed_result(
    *,
    project_id: ProjectId,
    run_id: RunId,
    expected_generation: int,
    projection_context: PreparedRelease | None = None,
) -> Select[int]:
    _request = _select_completed_resultRequest(
        project_id=project_id,
        run_id=run_id,
        expected_generation=expected_generation,
    )
    if projection_context is not None:
        require_call_context(
            projection_context,
            "select_result",
            "select_completed_result",
            SELECT_COMPLETED_RESULT_CONTRACT_DIGEST,
        )
    return _select_completed_result_statement.params(
        **{
            "project_id": _request.project_id,
            "run_id": _request.run_id,
            "expected_generation": _request.expected_generation,
        }
    )


_select_completed_result_adapter = TypeAdapter(int)


def materialize_select_completed_result(row: tuple[int]) -> int:
    with native_result_scope("select_result", "select_completed_result", "generation"):
        checked = _select_completed_result_adapter.validate_python(row[0], strict=True)
        return checked


def select_completed_result(
    conn: Connection,
    *,
    project_id: ProjectId,
    run_id: RunId,
    expected_generation: int,
    projection_context: PreparedRelease | None = None,
) -> int:
    _statement = prepare_select_completed_result(
        project_id=project_id,
        run_id=run_id,
        expected_generation=expected_generation,
        projection_context=projection_context,
    )
    _native_result = conn.execute(_statement)
    with native_result_scope("select_result", "select_completed_result"):
        row = _native_result.one()
        return materialize_select_completed_result(row)


RETAIN_PDF_ORIGINAL_CONTRACT_DIGEST = (
    "265e56efb01e56fb8ece5e7a0d683815d4c2f0432663d4eb5bd2f587cb6a7a53"
)


class _retain_pdf_originalRequest(OperationResult):
    task_id: Annotated[
        TaskId, Field(ge=TaskId(-9223372036854775808), le=TaskId(9223372036854775807))
    ]
    attempt: Annotated[
        TaskAttempt,
        Field(ge=TaskAttempt(-9223372036854775808), le=TaskAttempt(9223372036854775807)),
    ]
    holder: str
    original: bytes
    recipe_bytes: bytes


_retain_pdf_original_function = func.ops.retain_pdf_original(
    bindparam("task_id", type_=BigInteger()),
    bindparam("attempt", type_=BigInteger()),
    bindparam("holder", type_=Text()),
    bindparam("original", type_=BYTEA()),
    bindparam("recipe_bytes", type_=BYTEA()),
    type_=Text(),
)
_retain_pdf_original_statement = select(_retain_pdf_original_function)


def prepare_retain_pdf_original(
    *,
    task_id: TaskId,
    attempt: TaskAttempt,
    holder: str,
    original: bytes,
    recipe_bytes: bytes,
    projection_context: PreparedRelease | None = None,
) -> Select[str]:
    _request = _retain_pdf_originalRequest(
        task_id=task_id,
        attempt=attempt,
        holder=holder,
        original=original,
        recipe_bytes=recipe_bytes,
    )
    if projection_context is not None:
        require_call_context(
            projection_context,
            "retain_pdf_original",
            "retain_pdf_original",
            RETAIN_PDF_ORIGINAL_CONTRACT_DIGEST,
        )
    return _retain_pdf_original_statement.params(
        **{
            "task_id": _request.task_id,
            "attempt": _request.attempt,
            "holder": _request.holder,
            "original": _request.original,
            "recipe_bytes": _request.recipe_bytes,
        }
    )


_retain_pdf_original_adapter = TypeAdapter(str)


def materialize_retain_pdf_original(row: tuple[str]) -> str:
    with native_result_scope("retain_pdf_original", "retain_pdf_original", "digest"):
        checked = _retain_pdf_original_adapter.validate_python(row[0], strict=True)
        return checked


def retain_pdf_original(
    conn: Connection,
    *,
    task_id: TaskId,
    attempt: TaskAttempt,
    holder: str,
    original: bytes,
    recipe_bytes: bytes,
    projection_context: PreparedRelease | None = None,
) -> str:
    _statement = prepare_retain_pdf_original(
        task_id=task_id,
        attempt=attempt,
        holder=holder,
        original=original,
        recipe_bytes=recipe_bytes,
        projection_context=projection_context,
    )
    _native_result = conn.execute(_statement)
    with native_result_scope("retain_pdf_original", "retain_pdf_original"):
        row = _native_result.one()
        return materialize_retain_pdf_original(row)


PUBLISH_SOURCE_VIEW_CONTRACT_DIGEST = (
    "adfb2e0ff172e7b12982b5803a1561228dd8e7037d1979482fe4a0edb108f3f0"
)


class _publish_source_viewRequest(OperationResult):
    run_id: Annotated[RunId, Field(ge=RunId(-9223372036854775808), le=RunId(9223372036854775807))]
    task_id: Annotated[
        TaskId, Field(ge=TaskId(-9223372036854775808), le=TaskId(9223372036854775807))
    ]
    attempt: Annotated[
        TaskAttempt,
        Field(ge=TaskAttempt(-9223372036854775808), le=TaskAttempt(9223372036854775807)),
    ]
    holder: str
    position: Annotated[int, Field(ge=-9223372036854775808, le=9223372036854775807)]
    payload: bytes
    recipe: bytes


_publish_source_view_function = func.ops.publish_source_view(
    bindparam("run_id", type_=BigInteger()),
    bindparam("task_id", type_=BigInteger()),
    bindparam("attempt", type_=BigInteger()),
    bindparam("holder", type_=Text()),
    bindparam("position", type_=BigInteger()),
    bindparam("payload", type_=BYTEA()),
    bindparam("recipe", type_=BYTEA()),
    type_=BigInteger(),
)
_publish_source_view_statement = select(_publish_source_view_function)


def prepare_publish_source_view(
    *,
    run_id: RunId,
    task_id: TaskId,
    attempt: TaskAttempt,
    holder: str,
    position: int,
    payload: bytes,
    recipe: bytes,
    projection_context: PreparedRelease | None = None,
) -> Select[int]:
    _request = _publish_source_viewRequest(
        run_id=run_id,
        task_id=task_id,
        attempt=attempt,
        holder=holder,
        position=position,
        payload=payload,
        recipe=recipe,
    )
    if projection_context is not None:
        require_call_context(
            projection_context,
            "publish_source_view",
            "publish_source_view",
            PUBLISH_SOURCE_VIEW_CONTRACT_DIGEST,
        )
    return _publish_source_view_statement.params(
        **{
            "run_id": _request.run_id,
            "task_id": _request.task_id,
            "attempt": _request.attempt,
            "holder": _request.holder,
            "position": _request.position,
            "payload": _request.payload,
            "recipe": _request.recipe,
        }
    )


_publish_source_view_adapter = TypeAdapter(SourceViewId)


def materialize_publish_source_view(row: tuple[int]) -> SourceViewId:
    with native_result_scope("publish_source_view", "publish_source_view", "source_view_id"):
        checked = _publish_source_view_adapter.validate_python(row[0], strict=True)
        return checked


def publish_source_view(
    conn: Connection,
    *,
    run_id: RunId,
    task_id: TaskId,
    attempt: TaskAttempt,
    holder: str,
    position: int,
    payload: bytes,
    recipe: bytes,
    projection_context: PreparedRelease | None = None,
) -> SourceViewId:
    _statement = prepare_publish_source_view(
        run_id=run_id,
        task_id=task_id,
        attempt=attempt,
        holder=holder,
        position=position,
        payload=payload,
        recipe=recipe,
        projection_context=projection_context,
    )
    _native_result = conn.execute(_statement)
    with native_result_scope("publish_source_view", "publish_source_view"):
        row = _native_result.one()
        return materialize_publish_source_view(row)


SELECT_REUSED_SOURCE_VIEWS_CONTRACT_DIGEST = (
    "261c558a2ca34b1df5b59df8ba7ce82b762b0fa9697ae03369849fb6d60ba8d8"
)


class _select_reused_source_viewsRequest(OperationResult):
    run_id: Annotated[RunId, Field(ge=RunId(-9223372036854775808), le=RunId(9223372036854775807))]
    task_id: Annotated[
        TaskId, Field(ge=TaskId(-9223372036854775808), le=TaskId(9223372036854775807))
    ]


_select_reused_source_views_function = func.ops.select_reused_source_views(
    bindparam("run_id", type_=BigInteger()),
    bindparam("task_id", type_=BigInteger()),
)
_select_reused_source_views_statement = select(_select_reused_source_views_function)


def prepare_select_reused_source_views(
    *,
    run_id: RunId,
    task_id: TaskId,
    projection_context: PreparedRelease | None = None,
) -> Select[None]:
    _request = _select_reused_source_viewsRequest(
        run_id=run_id,
        task_id=task_id,
    )
    if projection_context is not None:
        require_call_context(
            projection_context,
            "publish_source_view",
            "select_reused_source_views",
            SELECT_REUSED_SOURCE_VIEWS_CONTRACT_DIGEST,
        )
    return _select_reused_source_views_statement.params(
        **{
            "run_id": _request.run_id,
            "task_id": _request.task_id,
        }
    )


def select_reused_source_views(
    conn: Connection,
    *,
    run_id: RunId,
    task_id: TaskId,
    projection_context: PreparedRelease | None = None,
) -> None:
    _statement = prepare_select_reused_source_views(
        run_id=run_id,
        task_id=task_id,
        projection_context=projection_context,
    )
    _native_result = conn.execute(_statement)
    with native_result_scope("publish_source_view", "select_reused_source_views"):
        _native_result.scalar_one()
    return None


SELECT_SOURCE_VIEW_CONTRACT_DIGEST = (
    "d815d3660936ca34496b749be8c4f536b63b022fd34efd200dd0c5dbeadf93af"
)


class _select_source_viewRequest(OperationResult):
    run_id: Annotated[RunId, Field(ge=RunId(-9223372036854775808), le=RunId(9223372036854775807))]
    source_run_id: Annotated[
        RunId, Field(ge=RunId(-9223372036854775808), le=RunId(9223372036854775807))
    ]
    source_view_id: Annotated[
        SourceViewId,
        Field(ge=SourceViewId(-9223372036854775808), le=SourceViewId(9223372036854775807)),
    ]


_select_source_view_function = func.ops.select_source_view(
    bindparam("run_id", type_=BigInteger()),
    bindparam("source_run_id", type_=BigInteger()),
    bindparam("source_view_id", type_=BigInteger()),
)
_select_source_view_statement = select(_select_source_view_function)


def prepare_select_source_view(
    *,
    run_id: RunId,
    source_run_id: RunId,
    source_view_id: SourceViewId,
    projection_context: PreparedRelease | None = None,
) -> Select[None]:
    _request = _select_source_viewRequest(
        run_id=run_id,
        source_run_id=source_run_id,
        source_view_id=source_view_id,
    )
    if projection_context is not None:
        require_call_context(
            projection_context,
            "publish_source_view",
            "select_source_view",
            SELECT_SOURCE_VIEW_CONTRACT_DIGEST,
        )
    return _select_source_view_statement.params(
        **{
            "run_id": _request.run_id,
            "source_run_id": _request.source_run_id,
            "source_view_id": _request.source_view_id,
        }
    )


def select_source_view(
    conn: Connection,
    *,
    run_id: RunId,
    source_run_id: RunId,
    source_view_id: SourceViewId,
    projection_context: PreparedRelease | None = None,
) -> None:
    _statement = prepare_select_source_view(
        run_id=run_id,
        source_run_id=source_run_id,
        source_view_id=source_view_id,
        projection_context=projection_context,
    )
    _native_result = conn.execute(_statement)
    with native_result_scope("publish_source_view", "select_source_view"):
        _native_result.scalar_one()
    return None


READ_PUBLISHED_SECTIONS_CONTRACT_DIGEST = (
    "2a71f61199e3c6d0b46f508fe7a6d6c56a1af4c38680ee03b2cafe3167258b49"
)


class PublishedSectionRow(NativeRowResult):
    pointer: str
    parent_pointer: str | None
    ordinal: int
    label: str
    content_layer: str
    name: str | None
    ancestors: tuple[str, ...]
    section_pointer: str | None
    text: str | None


class _read_published_sectionsRequest(OperationResult):
    task_id: Annotated[
        TaskId, Field(ge=TaskId(-9223372036854775808), le=TaskId(9223372036854775807))
    ]
    product_key: ProductKey
    content_digest: ContentDigest


_read_published_sections_function = func.ops.read_pdf_published_sections(
    bindparam("task_id", type_=BigInteger()),
    bindparam("product_key", type_=Text()),
    bindparam("content_digest", type_=Text()),
).table_valued(
    column("pointer", Text()),
    column("parent_pointer", Text()),
    column("ordinal", BigInteger()),
    column("label", Text()),
    column("content_layer", Text()),
    column("name", Text()),
    column("ancestors", ARRAY(Text())),
    column("section_pointer", Text()),
    column("text", Text()),
)


class _read_published_sectionsColumns(Protocol):
    pointer: Column[str]
    parent_pointer: Column[str | None]
    ordinal: Column[int]
    label: Column[str]
    content_layer: Column[str]
    name: Column[str | None]
    ancestors: Column[list[str]]
    section_pointer: Column[str | None]
    text: Column[str | None]


_read_published_sections_columns = cast(
    _read_published_sectionsColumns, _read_published_sections_function.c
)
_read_published_sections_statement = select(
    _read_published_sections_columns.pointer,
    _read_published_sections_columns.parent_pointer,
    _read_published_sections_columns.ordinal,
    _read_published_sections_columns.label,
    _read_published_sections_columns.content_layer,
    _read_published_sections_columns.name,
    _read_published_sections_columns.ancestors,
    _read_published_sections_columns.section_pointer,
    _read_published_sections_columns.text,
).order_by(
    _read_published_sections_columns.ordinal,
)


def _read_published_sections_result(
    row: tuple[str, str | None, int, str, str, str | None, list[str], str | None, str | None],
) -> PublishedSectionRow:
    with native_result_scope("read_native_source", "PublishedSectionRow"):
        return PublishedSectionRow(
            pointer=row[0],
            parent_pointer=row[1],
            ordinal=row[2],
            label=row[3],
            content_layer=row[4],
            name=row[5],
            ancestors=tuple(row[6]),
            section_pointer=row[7],
            text=row[8],
        )


def prepare_read_published_sections(
    *,
    task_id: TaskId,
    product_key: ProductKey,
    content_digest: ContentDigest,
    projection_context: PreparedRelease,
) -> Select[str, str | None, int, str, str, str | None, list[str], str | None, str | None]:
    _request = _read_published_sectionsRequest(
        task_id=task_id,
        product_key=product_key,
        content_digest=content_digest,
    )
    require_call_context(
        projection_context,
        "read_native_source",
        "read_published_sections",
        READ_PUBLISHED_SECTIONS_CONTRACT_DIGEST,
    )
    return _read_published_sections_statement.params(
        **{
            "task_id": _request.task_id,
            "product_key": _request.product_key,
            "content_digest": _request.content_digest,
        }
    )


materialize_read_published_sections = _read_published_sections_result


def read_published_sections(
    conn: Connection,
    *,
    task_id: TaskId,
    product_key: ProductKey,
    content_digest: ContentDigest,
    projection_context: PreparedRelease,
) -> tuple[PublishedSectionRow, ...]:
    _statement = prepare_read_published_sections(
        task_id=task_id,
        product_key=product_key,
        content_digest=content_digest,
        projection_context=projection_context,
    )
    _native_result = conn.execute(_statement)
    with native_result_scope("read_native_source", "PublishedSectionRow"):
        return tuple(_read_published_sections_result(row) for row in _native_result)


READ_PUBLISHED_SECTION_NODES_CONTRACT_DIGEST = (
    "2b0ebfe3691de2ffafdebe675890450e887bca9db0fc69065380e192dc7e62e9"
)


class PublishedSectionNodeRow(NativeRowResult):
    __json_fields__ = ("native_json",)
    role: Literal["ancestor", "selected"]
    product_id: str
    revision_id: str
    pointer: str
    ordinal: int
    label: str
    parent_pointer: str | None
    section_pointer: str | None
    content_layer: str
    text: str | None
    native_json: str


class _read_published_section_nodesRequest(OperationResult):
    task_id: Annotated[
        TaskId, Field(ge=TaskId(-9223372036854775808), le=TaskId(9223372036854775807))
    ]
    product_key: ProductKey
    content_digest: ContentDigest
    section: str
    membership: PdfSourceViewPublicationMembership


_read_published_section_nodes_function = func.ops.read_pdf_published_section_nodes(
    bindparam("task_id", type_=BigInteger()),
    bindparam("product_key", type_=Text()),
    bindparam("content_digest", type_=Text()),
    bindparam("section", type_=Text()),
    bindparam("membership", type_=Text()),
).table_valued(
    column("role", Text()),
    column("product_id", Text()),
    column("revision_id", Text()),
    column("pointer", Text()),
    column("ordinal", BigInteger()),
    column("label", Text()),
    column("parent_pointer", Text()),
    column("section_pointer", Text()),
    column("content_layer", Text()),
    column("text", Text()),
    column("native_json", JSONB()),
)


class _read_published_section_nodesColumns(Protocol):
    role: Column[str]
    product_id: Column[str]
    revision_id: Column[str]
    pointer: Column[str]
    ordinal: Column[int]
    label: Column[str]
    parent_pointer: Column[str | None]
    section_pointer: Column[str | None]
    content_layer: Column[str]
    text: Column[str | None]
    native_json: Column[JsonValue]


_read_published_section_nodes_columns = cast(
    _read_published_section_nodesColumns, _read_published_section_nodes_function.c
)
_read_published_section_nodes_statement = select(
    _read_published_section_nodes_columns.role,
    _read_published_section_nodes_columns.product_id,
    _read_published_section_nodes_columns.revision_id,
    _read_published_section_nodes_columns.pointer,
    _read_published_section_nodes_columns.ordinal,
    _read_published_section_nodes_columns.label,
    _read_published_section_nodes_columns.parent_pointer,
    _read_published_section_nodes_columns.section_pointer,
    _read_published_section_nodes_columns.content_layer,
    _read_published_section_nodes_columns.text,
    _read_published_section_nodes_columns.native_json.cast(Text()).label("native_json"),
).order_by(
    _read_published_section_nodes_columns.ordinal,
)


def _read_published_section_nodes_result(
    row: tuple[str, str, str, str, int, str, str | None, str | None, str, str | None, str],
) -> PublishedSectionNodeRow:
    with native_result_scope("read_native_source", "PublishedSectionNodeRow"):
        return PublishedSectionNodeRow(
            role=cast(Literal["ancestor", "selected"], row[0]),
            product_id=row[1],
            revision_id=row[2],
            pointer=row[3],
            ordinal=row[4],
            label=row[5],
            parent_pointer=row[6],
            section_pointer=row[7],
            content_layer=row[8],
            text=row[9],
            native_json=row[10],
        )


def prepare_read_published_section_nodes(
    *,
    task_id: TaskId,
    product_key: ProductKey,
    content_digest: ContentDigest,
    section: str,
    membership: PdfSourceViewPublicationMembership,
    projection_context: PreparedRelease,
) -> Select[str, str, str, str, int, str, str | None, str | None, str, str | None, str]:
    _request = _read_published_section_nodesRequest(
        task_id=task_id,
        product_key=product_key,
        content_digest=content_digest,
        section=section,
        membership=membership,
    )
    require_call_context(
        projection_context,
        "read_native_source",
        "read_published_section_nodes",
        READ_PUBLISHED_SECTION_NODES_CONTRACT_DIGEST,
    )
    return _read_published_section_nodes_statement.params(
        **{
            "task_id": _request.task_id,
            "product_key": _request.product_key,
            "content_digest": _request.content_digest,
            "section": _request.section,
            "membership": _request.membership,
        }
    )


materialize_read_published_section_nodes = _read_published_section_nodes_result


def read_published_section_nodes(
    conn: Connection,
    *,
    task_id: TaskId,
    product_key: ProductKey,
    content_digest: ContentDigest,
    section: str,
    membership: PdfSourceViewPublicationMembership,
    projection_context: PreparedRelease,
) -> tuple[PublishedSectionNodeRow, ...]:
    _statement = prepare_read_published_section_nodes(
        task_id=task_id,
        product_key=product_key,
        content_digest=content_digest,
        section=section,
        membership=membership,
        projection_context=projection_context,
    )
    _native_result = conn.execute(_statement)
    with native_result_scope("read_native_source", "PublishedSectionNodeRow"):
        return tuple(_read_published_section_nodes_result(row) for row in _native_result)


READ_PUBLISHED_ITEMS_CONTRACT_DIGEST = (
    "03feb8bc650d55ec5994ab8b78a4e040a745cae46ed3a4299c51a6af19a4bcb0"
)


class PdfRecordAccess(NativeRowResult):
    __json_fields__ = ("native_json",)
    product_id: str
    revision_id: str
    pointer: str
    ordinal: int
    label: str
    parent_pointer: str | None
    section_pointer: str | None
    content_layer: str
    text: str | None
    native_json: str


class _read_published_itemsRequest(OperationResult):
    task_id: Annotated[
        TaskId, Field(ge=TaskId(-9223372036854775808), le=TaskId(9223372036854775807))
    ]
    product_key: ProductKey
    content_digest: ContentDigest
    pointers: tuple[str, ...]


_read_published_items_function = func.ops.read_pdf_published_items(
    bindparam("task_id", type_=BigInteger()),
    bindparam("product_key", type_=Text()),
    bindparam("content_digest", type_=Text()),
    bindparam("pointers", type_=ARRAY(Text())),
).table_valued(
    column("product_id", Text()),
    column("revision_id", Text()),
    column("pointer", Text()),
    column("ordinal", BigInteger()),
    column("label", Text()),
    column("parent_pointer", Text()),
    column("section_pointer", Text()),
    column("content_layer", Text()),
    column("text", Text()),
    column("native_json", JSONB()),
)


class _read_published_itemsColumns(Protocol):
    product_id: Column[str]
    revision_id: Column[str]
    pointer: Column[str]
    ordinal: Column[int]
    label: Column[str]
    parent_pointer: Column[str | None]
    section_pointer: Column[str | None]
    content_layer: Column[str]
    text: Column[str | None]
    native_json: Column[JsonValue]


_read_published_items_columns = cast(_read_published_itemsColumns, _read_published_items_function.c)
_read_published_items_statement = select(
    _read_published_items_columns.product_id,
    _read_published_items_columns.revision_id,
    _read_published_items_columns.pointer,
    _read_published_items_columns.ordinal,
    _read_published_items_columns.label,
    _read_published_items_columns.parent_pointer,
    _read_published_items_columns.section_pointer,
    _read_published_items_columns.content_layer,
    _read_published_items_columns.text,
    _read_published_items_columns.native_json.cast(Text()).label("native_json"),
).order_by(
    _read_published_items_columns.ordinal,
)


def _read_published_items_result(
    row: tuple[str, str, str, int, str, str | None, str | None, str, str | None, str],
) -> PdfRecordAccess:
    with native_result_scope("read_native_source", "PdfRecordAccess"):
        return PdfRecordAccess(
            product_id=row[0],
            revision_id=row[1],
            pointer=row[2],
            ordinal=row[3],
            label=row[4],
            parent_pointer=row[5],
            section_pointer=row[6],
            content_layer=row[7],
            text=row[8],
            native_json=row[9],
        )


def prepare_read_published_items(
    *,
    task_id: TaskId,
    product_key: ProductKey,
    content_digest: ContentDigest,
    pointers: tuple[str, ...],
    projection_context: PreparedRelease,
) -> Select[str, str, str, int, str, str | None, str | None, str, str | None, str]:
    _request = _read_published_itemsRequest(
        task_id=task_id,
        product_key=product_key,
        content_digest=content_digest,
        pointers=pointers,
    )
    require_call_context(
        projection_context,
        "read_native_source",
        "read_published_items",
        READ_PUBLISHED_ITEMS_CONTRACT_DIGEST,
    )
    return _read_published_items_statement.params(
        **{
            "task_id": _request.task_id,
            "product_key": _request.product_key,
            "content_digest": _request.content_digest,
            "pointers": _request.pointers,
        }
    )


materialize_read_published_items = _read_published_items_result


def read_published_items(
    conn: Connection,
    *,
    task_id: TaskId,
    product_key: ProductKey,
    content_digest: ContentDigest,
    pointers: tuple[str, ...],
    projection_context: PreparedRelease,
) -> tuple[PdfRecordAccess, ...]:
    _statement = prepare_read_published_items(
        task_id=task_id,
        product_key=product_key,
        content_digest=content_digest,
        pointers=pointers,
        projection_context=projection_context,
    )
    _native_result = conn.execute(_statement)
    with native_result_scope("read_native_source", "PdfRecordAccess"):
        return tuple(_read_published_items_result(row) for row in _native_result)


READ_PUBLISHED_REGION_CONTRACT_DIGEST = (
    "6efdd34bf4c37193c1467311bd08d209c7aa3aeaa85dc46a36e07ca318341dba"
)


class PdfRecordRegion(NativeRowResult):
    product_id: str
    revision_id: str
    pointer: str
    region_index: int
    page_no: int
    page_width: Decimal
    page_height: Decimal
    left: Decimal
    top: Decimal
    right: Decimal
    bottom: Decimal
    origin: str


class _read_published_regionRequest(OperationResult):
    task_id: Annotated[
        TaskId, Field(ge=TaskId(-9223372036854775808), le=TaskId(9223372036854775807))
    ]
    product_key: ProductKey
    content_digest: ContentDigest
    pointer: str
    region_index: Annotated[int, Field(ge=-9223372036854775808, le=9223372036854775807)]


_read_published_region_function = func.ops.read_pdf_published_region(
    bindparam("task_id", type_=BigInteger()),
    bindparam("product_key", type_=Text()),
    bindparam("content_digest", type_=Text()),
    bindparam("pointer", type_=Text()),
    bindparam("region_index", type_=BigInteger()),
).table_valued(
    column("product_id", Text()),
    column("revision_id", Text()),
    column("pointer", Text()),
    column("region_index", BigInteger()),
    column("page_no", BigInteger()),
    column("page_width", Numeric()),
    column("page_height", Numeric()),
    column("left", Numeric()),
    column("top", Numeric()),
    column("right", Numeric()),
    column("bottom", Numeric()),
    column("origin", Text()),
)


class _read_published_regionColumns(Protocol):
    product_id: Column[str]
    revision_id: Column[str]
    pointer: Column[str]
    region_index: Column[int]
    page_no: Column[int]
    page_width: Column[Decimal]
    page_height: Column[Decimal]
    left: Column[Decimal]
    top: Column[Decimal]
    right: Column[Decimal]
    bottom: Column[Decimal]
    origin: Column[str]


_read_published_region_columns = cast(
    _read_published_regionColumns, _read_published_region_function.c
)
_read_published_region_statement = select(
    _read_published_region_columns.product_id,
    _read_published_region_columns.revision_id,
    _read_published_region_columns.pointer,
    _read_published_region_columns.region_index,
    _read_published_region_columns.page_no,
    _read_published_region_columns.page_width,
    _read_published_region_columns.page_height,
    _read_published_region_columns.left,
    _read_published_region_columns.top,
    _read_published_region_columns.right,
    _read_published_region_columns.bottom,
    _read_published_region_columns.origin,
)


def _read_published_region_result(
    row: tuple[str, str, str, int, int, Decimal, Decimal, Decimal, Decimal, Decimal, Decimal, str],
) -> PdfRecordRegion:
    with native_result_scope("read_native_source", "PdfRecordRegion"):
        return PdfRecordRegion(
            product_id=row[0],
            revision_id=row[1],
            pointer=row[2],
            region_index=row[3],
            page_no=row[4],
            page_width=row[5],
            page_height=row[6],
            left=row[7],
            top=row[8],
            right=row[9],
            bottom=row[10],
            origin=row[11],
        )


def prepare_read_published_region(
    *,
    task_id: TaskId,
    product_key: ProductKey,
    content_digest: ContentDigest,
    pointer: str,
    region_index: int,
    projection_context: PreparedRelease,
) -> Select[str, str, str, int, int, Decimal, Decimal, Decimal, Decimal, Decimal, Decimal, str]:
    _request = _read_published_regionRequest(
        task_id=task_id,
        product_key=product_key,
        content_digest=content_digest,
        pointer=pointer,
        region_index=region_index,
    )
    require_call_context(
        projection_context,
        "read_native_source",
        "read_published_region",
        READ_PUBLISHED_REGION_CONTRACT_DIGEST,
    )
    return _read_published_region_statement.params(
        **{
            "task_id": _request.task_id,
            "product_key": _request.product_key,
            "content_digest": _request.content_digest,
            "pointer": _request.pointer,
            "region_index": _request.region_index,
        }
    )


materialize_read_published_region = _read_published_region_result


def read_published_region(
    conn: Connection,
    *,
    task_id: TaskId,
    product_key: ProductKey,
    content_digest: ContentDigest,
    pointer: str,
    region_index: int,
    projection_context: PreparedRelease,
) -> PdfRecordRegion | None:
    _statement = prepare_read_published_region(
        task_id=task_id,
        product_key=product_key,
        content_digest=content_digest,
        pointer=pointer,
        region_index=region_index,
        projection_context=projection_context,
    )
    _native_result = conn.execute(_statement)
    with native_result_scope("read_native_source", "PdfRecordRegion"):
        row = _native_result.one_or_none()
        return None if row is None else _read_published_region_result(row)


READ_PUBLISHED_SECTION_REPORTS_CONTRACT_DIGEST = (
    "764f44f84ef4fc30a5a9801caf6aadb5692d9d2cdb97d1e136a5c86c6eb38c50"
)


class PublishedSectionReportRow(NativeRowResult):
    __json_fields__ = ("body",)
    local_id: str
    ordinal: int
    body: str


class _read_published_section_reportsRequest(OperationResult):
    task_id: Annotated[
        TaskId, Field(ge=TaskId(-9223372036854775808), le=TaskId(9223372036854775807))
    ]
    product_key: ProductKey
    content_digest: ContentDigest
    pointers: tuple[str, ...]
    sections: tuple[str, ...]


_read_published_section_reports_function = func.ops.read_pdf_published_section_reports(
    bindparam("task_id", type_=BigInteger()),
    bindparam("product_key", type_=Text()),
    bindparam("content_digest", type_=Text()),
    bindparam("pointers", type_=ARRAY(Text())),
    bindparam("sections", type_=ARRAY(Text())),
).table_valued(
    column("local_id", Text()),
    column("ordinal", BigInteger()),
    column("body", JSONB()),
)


class _read_published_section_reportsColumns(Protocol):
    local_id: Column[str]
    ordinal: Column[int]
    body: Column[JsonValue]


_read_published_section_reports_columns = cast(
    _read_published_section_reportsColumns, _read_published_section_reports_function.c
)
_read_published_section_reports_statement = select(
    _read_published_section_reports_columns.local_id,
    _read_published_section_reports_columns.ordinal,
    _read_published_section_reports_columns.body.cast(Text()).label("body"),
).order_by(
    _read_published_section_reports_columns.ordinal,
    _read_published_section_reports_columns.local_id.collate("C"),
)


def _read_published_section_reports_result(row: tuple[str, int, str]) -> PublishedSectionReportRow:
    with native_result_scope("read_native_source", "PublishedSectionReportRow"):
        return PublishedSectionReportRow(
            local_id=row[0],
            ordinal=row[1],
            body=row[2],
        )


def prepare_read_published_section_reports(
    *,
    task_id: TaskId,
    product_key: ProductKey,
    content_digest: ContentDigest,
    pointers: tuple[str, ...],
    sections: tuple[str, ...],
    projection_context: PreparedRelease,
) -> Select[str, int, str]:
    _request = _read_published_section_reportsRequest(
        task_id=task_id,
        product_key=product_key,
        content_digest=content_digest,
        pointers=pointers,
        sections=sections,
    )
    require_call_context(
        projection_context,
        "read_native_source",
        "read_published_section_reports",
        READ_PUBLISHED_SECTION_REPORTS_CONTRACT_DIGEST,
    )
    return _read_published_section_reports_statement.params(
        **{
            "task_id": _request.task_id,
            "product_key": _request.product_key,
            "content_digest": _request.content_digest,
            "pointers": _request.pointers,
            "sections": _request.sections,
        }
    )


materialize_read_published_section_reports = _read_published_section_reports_result


def read_published_section_reports(
    conn: Connection,
    *,
    task_id: TaskId,
    product_key: ProductKey,
    content_digest: ContentDigest,
    pointers: tuple[str, ...],
    sections: tuple[str, ...],
    projection_context: PreparedRelease,
) -> tuple[PublishedSectionReportRow, ...]:
    _statement = prepare_read_published_section_reports(
        task_id=task_id,
        product_key=product_key,
        content_digest=content_digest,
        pointers=pointers,
        sections=sections,
        projection_context=projection_context,
    )
    _native_result = conn.execute(_statement)
    with native_result_scope("read_native_source", "PublishedSectionReportRow"):
        return tuple(_read_published_section_reports_result(row) for row in _native_result)


READ_PUBLISHED_ITEM_PAGE_CONTRACT_DIGEST = (
    "11363376105f61feab8dfd19a1d746d1e6360499e365a9085f10f11f218f4c52"
)


class PublishedItemIndexRow(NativeRowResult):
    product_id: str
    revision_id: str
    pointer: str
    ordinal: int
    label: str
    parent_pointer: str | None
    section_pointer: str | None
    content_layer: str
    text: str | None


class _read_published_item_pageRequest(OperationResult):
    task_id: Annotated[
        TaskId, Field(ge=TaskId(-9223372036854775808), le=TaskId(9223372036854775807))
    ]
    product_key: ProductKey
    content_digest: ContentDigest
    section: str | None
    membership: PdfSourceViewPublicationMembership
    pointer: str | None
    after: Annotated[int, Field(ge=-9223372036854775808, le=9223372036854775807)]
    limit: Annotated[int, Field(ge=-9223372036854775808, le=9223372036854775807)]


_read_published_item_page_function = func.ops.read_pdf_published_item_page(
    bindparam("task_id", type_=BigInteger()),
    bindparam("product_key", type_=Text()),
    bindparam("content_digest", type_=Text()),
    bindparam("section", type_=Text()),
    bindparam("membership", type_=Text()),
    bindparam("pointer", type_=Text()),
    bindparam("after", type_=BigInteger()),
    bindparam("limit", type_=BigInteger()),
).table_valued(
    column("product_id", Text()),
    column("revision_id", Text()),
    column("pointer", Text()),
    column("ordinal", BigInteger()),
    column("label", Text()),
    column("parent_pointer", Text()),
    column("section_pointer", Text()),
    column("content_layer", Text()),
    column("text", Text()),
)


class _read_published_item_pageColumns(Protocol):
    product_id: Column[str]
    revision_id: Column[str]
    pointer: Column[str]
    ordinal: Column[int]
    label: Column[str]
    parent_pointer: Column[str | None]
    section_pointer: Column[str | None]
    content_layer: Column[str]
    text: Column[str | None]


_read_published_item_page_columns = cast(
    _read_published_item_pageColumns, _read_published_item_page_function.c
)
_read_published_item_page_statement = select(
    _read_published_item_page_columns.product_id,
    _read_published_item_page_columns.revision_id,
    _read_published_item_page_columns.pointer,
    _read_published_item_page_columns.ordinal,
    _read_published_item_page_columns.label,
    _read_published_item_page_columns.parent_pointer,
    _read_published_item_page_columns.section_pointer,
    _read_published_item_page_columns.content_layer,
    _read_published_item_page_columns.text,
).order_by(
    _read_published_item_page_columns.ordinal,
)


def _read_published_item_page_result(
    row: tuple[str, str, str, int, str, str | None, str | None, str, str | None],
) -> PublishedItemIndexRow:
    with native_result_scope("read_native_source", "PublishedItemIndexRow"):
        return PublishedItemIndexRow(
            product_id=row[0],
            revision_id=row[1],
            pointer=row[2],
            ordinal=row[3],
            label=row[4],
            parent_pointer=row[5],
            section_pointer=row[6],
            content_layer=row[7],
            text=row[8],
        )


def prepare_read_published_item_page(
    *,
    task_id: TaskId,
    product_key: ProductKey,
    content_digest: ContentDigest,
    section: str | None,
    membership: PdfSourceViewPublicationMembership,
    pointer: str | None,
    after: int,
    limit: int,
    projection_context: PreparedRelease,
) -> Select[str, str, str, int, str, str | None, str | None, str, str | None]:
    _request = _read_published_item_pageRequest(
        task_id=task_id,
        product_key=product_key,
        content_digest=content_digest,
        section=section,
        membership=membership,
        pointer=pointer,
        after=after,
        limit=limit,
    )
    require_call_context(
        projection_context,
        "read_native_source",
        "read_published_item_page",
        READ_PUBLISHED_ITEM_PAGE_CONTRACT_DIGEST,
    )
    return _read_published_item_page_statement.params(
        **{
            "task_id": _request.task_id,
            "product_key": _request.product_key,
            "content_digest": _request.content_digest,
            "section": _request.section,
            "membership": _request.membership,
            "pointer": _request.pointer,
            "after": _request.after,
            "limit": _request.limit,
        }
    )


materialize_read_published_item_page = _read_published_item_page_result


def read_published_item_page(
    conn: Connection,
    *,
    task_id: TaskId,
    product_key: ProductKey,
    content_digest: ContentDigest,
    section: str | None,
    membership: PdfSourceViewPublicationMembership,
    pointer: str | None,
    after: int,
    limit: int,
    projection_context: PreparedRelease,
) -> tuple[PublishedItemIndexRow, ...]:
    _statement = prepare_read_published_item_page(
        task_id=task_id,
        product_key=product_key,
        content_digest=content_digest,
        section=section,
        membership=membership,
        pointer=pointer,
        after=after,
        limit=limit,
        projection_context=projection_context,
    )
    _native_result = conn.execute(_statement)
    with native_result_scope("read_native_source", "PublishedItemIndexRow"):
        return tuple(_read_published_item_page_result(row) for row in _native_result)


READ_PUBLISHED_REGIONS_CONTRACT_DIGEST = (
    "6213dd4ef22a3fecf9d03cc87619c43443255956dd6c5b6a75887a4740a276b6"
)


class _read_published_regionsRequest(OperationResult):
    task_id: Annotated[
        TaskId, Field(ge=TaskId(-9223372036854775808), le=TaskId(9223372036854775807))
    ]
    product_key: ProductKey
    content_digest: ContentDigest
    pointer: str


_read_published_regions_function = func.ops.read_pdf_published_regions(
    bindparam("task_id", type_=BigInteger()),
    bindparam("product_key", type_=Text()),
    bindparam("content_digest", type_=Text()),
    bindparam("pointer", type_=Text()),
).table_valued(
    column("product_id", Text()),
    column("revision_id", Text()),
    column("pointer", Text()),
    column("region_index", BigInteger()),
    column("page_no", BigInteger()),
    column("page_width", Numeric()),
    column("page_height", Numeric()),
    column("left", Numeric()),
    column("top", Numeric()),
    column("right", Numeric()),
    column("bottom", Numeric()),
    column("origin", Text()),
)


class _read_published_regionsColumns(Protocol):
    product_id: Column[str]
    revision_id: Column[str]
    pointer: Column[str]
    region_index: Column[int]
    page_no: Column[int]
    page_width: Column[Decimal]
    page_height: Column[Decimal]
    left: Column[Decimal]
    top: Column[Decimal]
    right: Column[Decimal]
    bottom: Column[Decimal]
    origin: Column[str]


_read_published_regions_columns = cast(
    _read_published_regionsColumns, _read_published_regions_function.c
)
_read_published_regions_statement = select(
    _read_published_regions_columns.product_id,
    _read_published_regions_columns.revision_id,
    _read_published_regions_columns.pointer,
    _read_published_regions_columns.region_index,
    _read_published_regions_columns.page_no,
    _read_published_regions_columns.page_width,
    _read_published_regions_columns.page_height,
    _read_published_regions_columns.left,
    _read_published_regions_columns.top,
    _read_published_regions_columns.right,
    _read_published_regions_columns.bottom,
    _read_published_regions_columns.origin,
).order_by(
    _read_published_regions_columns.region_index,
)


def _read_published_regions_result(
    row: tuple[str, str, str, int, int, Decimal, Decimal, Decimal, Decimal, Decimal, Decimal, str],
) -> PdfRecordRegion:
    with native_result_scope("read_native_source", "PdfRecordRegion"):
        return PdfRecordRegion(
            product_id=row[0],
            revision_id=row[1],
            pointer=row[2],
            region_index=row[3],
            page_no=row[4],
            page_width=row[5],
            page_height=row[6],
            left=row[7],
            top=row[8],
            right=row[9],
            bottom=row[10],
            origin=row[11],
        )


def prepare_read_published_regions(
    *,
    task_id: TaskId,
    product_key: ProductKey,
    content_digest: ContentDigest,
    pointer: str,
    projection_context: PreparedRelease,
) -> Select[str, str, str, int, int, Decimal, Decimal, Decimal, Decimal, Decimal, Decimal, str]:
    _request = _read_published_regionsRequest(
        task_id=task_id,
        product_key=product_key,
        content_digest=content_digest,
        pointer=pointer,
    )
    require_call_context(
        projection_context,
        "read_native_source",
        "read_published_regions",
        READ_PUBLISHED_REGIONS_CONTRACT_DIGEST,
    )
    return _read_published_regions_statement.params(
        **{
            "task_id": _request.task_id,
            "product_key": _request.product_key,
            "content_digest": _request.content_digest,
            "pointer": _request.pointer,
        }
    )


materialize_read_published_regions = _read_published_regions_result


def read_published_regions(
    conn: Connection,
    *,
    task_id: TaskId,
    product_key: ProductKey,
    content_digest: ContentDigest,
    pointer: str,
    projection_context: PreparedRelease,
) -> tuple[PdfRecordRegion, ...]:
    _statement = prepare_read_published_regions(
        task_id=task_id,
        product_key=product_key,
        content_digest=content_digest,
        pointer=pointer,
        projection_context=projection_context,
    )
    _native_result = conn.execute(_statement)
    with native_result_scope("read_native_source", "PdfRecordRegion"):
        return tuple(_read_published_regions_result(row) for row in _native_result)


READ_PUBLISHED_REGION_BATCH_CONTRACT_DIGEST = (
    "adae16e71ea3ab3307b24af47ff7a5210c38eab6bebbf31891e6f27fd1c49828"
)


class _read_published_region_batchRequest(OperationResult):
    task_id: Annotated[
        TaskId, Field(ge=TaskId(-9223372036854775808), le=TaskId(9223372036854775807))
    ]
    product_key: ProductKey
    content_digest: ContentDigest
    pointers: tuple[str, ...]


_read_published_region_batch_function = func.ops.read_pdf_published_region_batch(
    bindparam("task_id", type_=BigInteger()),
    bindparam("product_key", type_=Text()),
    bindparam("content_digest", type_=Text()),
    bindparam("pointers", type_=ARRAY(Text())),
).table_valued(
    column("product_id", Text()),
    column("revision_id", Text()),
    column("pointer", Text()),
    column("region_index", BigInteger()),
    column("page_no", BigInteger()),
    column("page_width", Numeric()),
    column("page_height", Numeric()),
    column("left", Numeric()),
    column("top", Numeric()),
    column("right", Numeric()),
    column("bottom", Numeric()),
    column("origin", Text()),
)


class _read_published_region_batchColumns(Protocol):
    product_id: Column[str]
    revision_id: Column[str]
    pointer: Column[str]
    region_index: Column[int]
    page_no: Column[int]
    page_width: Column[Decimal]
    page_height: Column[Decimal]
    left: Column[Decimal]
    top: Column[Decimal]
    right: Column[Decimal]
    bottom: Column[Decimal]
    origin: Column[str]


_read_published_region_batch_columns = cast(
    _read_published_region_batchColumns, _read_published_region_batch_function.c
)
_read_published_region_batch_statement = select(
    _read_published_region_batch_columns.product_id,
    _read_published_region_batch_columns.revision_id,
    _read_published_region_batch_columns.pointer,
    _read_published_region_batch_columns.region_index,
    _read_published_region_batch_columns.page_no,
    _read_published_region_batch_columns.page_width,
    _read_published_region_batch_columns.page_height,
    _read_published_region_batch_columns.left,
    _read_published_region_batch_columns.top,
    _read_published_region_batch_columns.right,
    _read_published_region_batch_columns.bottom,
    _read_published_region_batch_columns.origin,
).order_by(
    _read_published_region_batch_columns.pointer.collate("C"),
    _read_published_region_batch_columns.region_index,
)


def _read_published_region_batch_result(
    row: tuple[str, str, str, int, int, Decimal, Decimal, Decimal, Decimal, Decimal, Decimal, str],
) -> PdfRecordRegion:
    with native_result_scope("read_native_source", "PdfRecordRegion"):
        return PdfRecordRegion(
            product_id=row[0],
            revision_id=row[1],
            pointer=row[2],
            region_index=row[3],
            page_no=row[4],
            page_width=row[5],
            page_height=row[6],
            left=row[7],
            top=row[8],
            right=row[9],
            bottom=row[10],
            origin=row[11],
        )


def prepare_read_published_region_batch(
    *,
    task_id: TaskId,
    product_key: ProductKey,
    content_digest: ContentDigest,
    pointers: tuple[str, ...],
    projection_context: PreparedRelease,
) -> Select[str, str, str, int, int, Decimal, Decimal, Decimal, Decimal, Decimal, Decimal, str]:
    _request = _read_published_region_batchRequest(
        task_id=task_id,
        product_key=product_key,
        content_digest=content_digest,
        pointers=pointers,
    )
    require_call_context(
        projection_context,
        "read_native_source",
        "read_published_region_batch",
        READ_PUBLISHED_REGION_BATCH_CONTRACT_DIGEST,
    )
    return _read_published_region_batch_statement.params(
        **{
            "task_id": _request.task_id,
            "product_key": _request.product_key,
            "content_digest": _request.content_digest,
            "pointers": _request.pointers,
        }
    )


materialize_read_published_region_batch = _read_published_region_batch_result


def read_published_region_batch(
    conn: Connection,
    *,
    task_id: TaskId,
    product_key: ProductKey,
    content_digest: ContentDigest,
    pointers: tuple[str, ...],
    projection_context: PreparedRelease,
) -> tuple[PdfRecordRegion, ...]:
    _statement = prepare_read_published_region_batch(
        task_id=task_id,
        product_key=product_key,
        content_digest=content_digest,
        pointers=pointers,
        projection_context=projection_context,
    )
    _native_result = conn.execute(_statement)
    with native_result_scope("read_native_source", "PdfRecordRegion"):
        return tuple(_read_published_region_batch_result(row) for row in _native_result)


READ_PUBLISHED_ITEM_ANCESTORS_CONTRACT_DIGEST = (
    "70c18d098016bbd03901f9605b6ad5bb50783ae8d6013953cb9d9cde46ca2b80"
)


class _read_published_item_ancestorsRequest(OperationResult):
    task_id: Annotated[
        TaskId, Field(ge=TaskId(-9223372036854775808), le=TaskId(9223372036854775807))
    ]
    product_key: ProductKey
    content_digest: ContentDigest
    pointer: str


_read_published_item_ancestors_function = func.ops.read_pdf_published_item_ancestors(
    bindparam("task_id", type_=BigInteger()),
    bindparam("product_key", type_=Text()),
    bindparam("content_digest", type_=Text()),
    bindparam("pointer", type_=Text()),
).table_valued(
    column("product_id", Text()),
    column("revision_id", Text()),
    column("pointer", Text()),
    column("ordinal", BigInteger()),
    column("label", Text()),
    column("parent_pointer", Text()),
    column("section_pointer", Text()),
    column("content_layer", Text()),
    column("text", Text()),
)


class _read_published_item_ancestorsColumns(Protocol):
    product_id: Column[str]
    revision_id: Column[str]
    pointer: Column[str]
    ordinal: Column[int]
    label: Column[str]
    parent_pointer: Column[str | None]
    section_pointer: Column[str | None]
    content_layer: Column[str]
    text: Column[str | None]


_read_published_item_ancestors_columns = cast(
    _read_published_item_ancestorsColumns, _read_published_item_ancestors_function.c
)
_read_published_item_ancestors_statement = select(
    _read_published_item_ancestors_columns.product_id,
    _read_published_item_ancestors_columns.revision_id,
    _read_published_item_ancestors_columns.pointer,
    _read_published_item_ancestors_columns.ordinal,
    _read_published_item_ancestors_columns.label,
    _read_published_item_ancestors_columns.parent_pointer,
    _read_published_item_ancestors_columns.section_pointer,
    _read_published_item_ancestors_columns.content_layer,
    _read_published_item_ancestors_columns.text,
).order_by(
    _read_published_item_ancestors_columns.ordinal,
)


def _read_published_item_ancestors_result(
    row: tuple[str, str, str, int, str, str | None, str | None, str, str | None],
) -> PublishedItemIndexRow:
    with native_result_scope("read_native_source", "PublishedItemIndexRow"):
        return PublishedItemIndexRow(
            product_id=row[0],
            revision_id=row[1],
            pointer=row[2],
            ordinal=row[3],
            label=row[4],
            parent_pointer=row[5],
            section_pointer=row[6],
            content_layer=row[7],
            text=row[8],
        )


def prepare_read_published_item_ancestors(
    *,
    task_id: TaskId,
    product_key: ProductKey,
    content_digest: ContentDigest,
    pointer: str,
    projection_context: PreparedRelease,
) -> Select[str, str, str, int, str, str | None, str | None, str, str | None]:
    _request = _read_published_item_ancestorsRequest(
        task_id=task_id,
        product_key=product_key,
        content_digest=content_digest,
        pointer=pointer,
    )
    require_call_context(
        projection_context,
        "read_native_source",
        "read_published_item_ancestors",
        READ_PUBLISHED_ITEM_ANCESTORS_CONTRACT_DIGEST,
    )
    return _read_published_item_ancestors_statement.params(
        **{
            "task_id": _request.task_id,
            "product_key": _request.product_key,
            "content_digest": _request.content_digest,
            "pointer": _request.pointer,
        }
    )


materialize_read_published_item_ancestors = _read_published_item_ancestors_result


def read_published_item_ancestors(
    conn: Connection,
    *,
    task_id: TaskId,
    product_key: ProductKey,
    content_digest: ContentDigest,
    pointer: str,
    projection_context: PreparedRelease,
) -> tuple[PublishedItemIndexRow, ...]:
    _statement = prepare_read_published_item_ancestors(
        task_id=task_id,
        product_key=product_key,
        content_digest=content_digest,
        pointer=pointer,
        projection_context=projection_context,
    )
    _native_result = conn.execute(_statement)
    with native_result_scope("read_native_source", "PublishedItemIndexRow"):
        return tuple(_read_published_item_ancestors_result(row) for row in _native_result)


READ_PDF_RECORD_ROWS_CONTRACT_DIGEST = (
    "c0e24a5b8f24567e60f507846cc8bc0c992a3c4578712bcaaf31e7b834d59a69"
)


class NativeJsonEnvelope(NativeRowResult):
    __json_fields__ = ("body",)
    body: str


class _read_pdf_record_rowsRequest(OperationResult):
    task_id: Annotated[
        TaskId, Field(ge=TaskId(-9223372036854775808), le=TaskId(9223372036854775807))
    ]
    product_key: ProductKey
    content_digest: ContentDigest
    family: str
    filters: JsonValue
    after: JsonValue | None
    limit: Annotated[int, Field(ge=-2147483648, le=2147483647)]


_read_pdf_record_rows_function = func.ops.read_pdf_record_rows(
    bindparam("task_id", type_=BigInteger()),
    bindparam("product_key", type_=Text()),
    bindparam("content_digest", type_=Text()),
    bindparam("family", type_=Text()),
    bindparam("filters", type_=JSONB()),
    bindparam("after", type_=JSONB(none_as_null=True)),
    bindparam("limit", type_=Integer()),
    type_=JSONB(),
)
_read_pdf_record_rows_statement = select(_read_pdf_record_rows_function.cast(Text()))


def prepare_read_pdf_record_rows(
    *,
    task_id: TaskId,
    product_key: ProductKey,
    content_digest: ContentDigest,
    family: str,
    filters: JsonValue,
    after: JsonValue | None,
    limit: int,
    projection_context: PreparedRelease | None = None,
) -> Select[str]:
    _request = _read_pdf_record_rowsRequest(
        task_id=task_id,
        product_key=product_key,
        content_digest=content_digest,
        family=family,
        filters=filters,
        after=after,
        limit=limit,
    )
    if projection_context is not None:
        require_call_context(
            projection_context,
            "read_native_source",
            "read_pdf_record_rows",
            READ_PDF_RECORD_ROWS_CONTRACT_DIGEST,
        )
    return _read_pdf_record_rows_statement.params(
        **{
            "task_id": _request.task_id,
            "product_key": _request.product_key,
            "content_digest": _request.content_digest,
            "family": _request.family,
            "filters": _request.filters,
            "after": _request.after,
            "limit": _request.limit,
        }
    )


_read_pdf_record_rows_adapter = TypeAdapter(str)


def materialize_read_pdf_record_rows(row: tuple[str]) -> NativeJsonEnvelope:
    with native_result_scope("read_native_source", "NativeJsonEnvelope", "body"):
        checked = _read_pdf_record_rows_adapter.validate_python(row[0], strict=True)
        return NativeJsonEnvelope(body=checked)


def read_pdf_record_rows(
    conn: Connection,
    *,
    task_id: TaskId,
    product_key: ProductKey,
    content_digest: ContentDigest,
    family: str,
    filters: JsonValue,
    after: JsonValue | None,
    limit: int,
    projection_context: PreparedRelease | None = None,
) -> tuple[NativeJsonEnvelope, ...]:
    _statement = prepare_read_pdf_record_rows(
        task_id=task_id,
        product_key=product_key,
        content_digest=content_digest,
        family=family,
        filters=filters,
        after=after,
        limit=limit,
        projection_context=projection_context,
    )
    _native_result = conn.execute(_statement)
    with native_result_scope("read_native_source", "NativeJsonEnvelope"):
        return tuple(materialize_read_pdf_record_rows(row) for row in _native_result)


READ_PDF_RECORD_CONTEXT_ROWS_CONTRACT_DIGEST = (
    "03720ec843c4e711e68404482d3eacd0b61a39b40de385af12582dedfaa47333"
)


class _read_pdf_record_context_rowsRequest(OperationResult):
    task_id: Annotated[
        TaskId, Field(ge=TaskId(-9223372036854775808), le=TaskId(9223372036854775807))
    ]
    product_key: ProductKey
    content_digest: ContentDigest
    pointers: tuple[str, ...]
    section: str | None
    family: str
    after: str | None
    limit: Annotated[int, Field(ge=-2147483648, le=2147483647)]


_read_pdf_record_context_rows_function = func.ops.read_pdf_record_context_rows(
    bindparam("task_id", type_=BigInteger()),
    bindparam("product_key", type_=Text()),
    bindparam("content_digest", type_=Text()),
    bindparam("pointers", type_=ARRAY(Text())),
    bindparam("section", type_=Text()),
    bindparam("family", type_=Text()),
    bindparam("after", type_=Text()),
    bindparam("limit", type_=Integer()),
    type_=JSONB(),
)
_read_pdf_record_context_rows_statement = select(
    _read_pdf_record_context_rows_function.cast(Text())
)


def prepare_read_pdf_record_context_rows(
    *,
    task_id: TaskId,
    product_key: ProductKey,
    content_digest: ContentDigest,
    pointers: tuple[str, ...],
    section: str | None,
    family: str,
    after: str | None,
    limit: int,
    projection_context: PreparedRelease | None = None,
) -> Select[str]:
    _request = _read_pdf_record_context_rowsRequest(
        task_id=task_id,
        product_key=product_key,
        content_digest=content_digest,
        pointers=pointers,
        section=section,
        family=family,
        after=after,
        limit=limit,
    )
    if projection_context is not None:
        require_call_context(
            projection_context,
            "read_native_source",
            "read_pdf_record_context_rows",
            READ_PDF_RECORD_CONTEXT_ROWS_CONTRACT_DIGEST,
        )
    return _read_pdf_record_context_rows_statement.params(
        **{
            "task_id": _request.task_id,
            "product_key": _request.product_key,
            "content_digest": _request.content_digest,
            "pointers": _request.pointers,
            "section": _request.section,
            "family": _request.family,
            "after": _request.after,
            "limit": _request.limit,
        }
    )


_read_pdf_record_context_rows_adapter = TypeAdapter(str)


def materialize_read_pdf_record_context_rows(row: tuple[str]) -> NativeJsonEnvelope:
    with native_result_scope("read_native_source", "NativeJsonEnvelope", "body"):
        checked = _read_pdf_record_context_rows_adapter.validate_python(row[0], strict=True)
        return NativeJsonEnvelope(body=checked)


def read_pdf_record_context_rows(
    conn: Connection,
    *,
    task_id: TaskId,
    product_key: ProductKey,
    content_digest: ContentDigest,
    pointers: tuple[str, ...],
    section: str | None,
    family: str,
    after: str | None,
    limit: int,
    projection_context: PreparedRelease | None = None,
) -> tuple[NativeJsonEnvelope, ...]:
    _statement = prepare_read_pdf_record_context_rows(
        task_id=task_id,
        product_key=product_key,
        content_digest=content_digest,
        pointers=pointers,
        section=section,
        family=family,
        after=after,
        limit=limit,
        projection_context=projection_context,
    )
    _native_result = conn.execute(_statement)
    with native_result_scope("read_native_source", "NativeJsonEnvelope"):
        return tuple(materialize_read_pdf_record_context_rows(row) for row in _native_result)


READ_PDF_COMPANION_EXPORT_EVENTS_CONTRACT_DIGEST = (
    "972e18a629674004226b09510486fb88dce67d2bfbe626e868ffde06a4dc8d44"
)


class _read_pdf_companion_export_eventsRequest(OperationResult):
    task_id: Annotated[
        TaskId, Field(ge=TaskId(-9223372036854775808), le=TaskId(9223372036854775807))
    ]
    product_key: ProductKey
    content_digest: ContentDigest
    family: str


_read_pdf_companion_export_events_function = func.ops.read_pdf_companion_export_events(
    bindparam("task_id", type_=BigInteger()),
    bindparam("product_key", type_=Text()),
    bindparam("content_digest", type_=Text()),
    bindparam("family", type_=Text()),
    type_=JSONB(),
)
_read_pdf_companion_export_events_statement = select(
    _read_pdf_companion_export_events_function.cast(Text())
)


def prepare_read_pdf_companion_export_events(
    *,
    task_id: TaskId,
    product_key: ProductKey,
    content_digest: ContentDigest,
    family: str,
    projection_context: PreparedRelease | None = None,
) -> Select[str]:
    _request = _read_pdf_companion_export_eventsRequest(
        task_id=task_id,
        product_key=product_key,
        content_digest=content_digest,
        family=family,
    )
    if projection_context is not None:
        require_call_context(
            projection_context,
            "read_native_source",
            "read_pdf_companion_export_events",
            READ_PDF_COMPANION_EXPORT_EVENTS_CONTRACT_DIGEST,
        )
    return _read_pdf_companion_export_events_statement.params(
        **{
            "task_id": _request.task_id,
            "product_key": _request.product_key,
            "content_digest": _request.content_digest,
            "family": _request.family,
        }
    )


_read_pdf_companion_export_events_adapter = TypeAdapter(str)


def materialize_read_pdf_companion_export_events(row: tuple[str]) -> NativeJsonEnvelope:
    with native_result_scope("read_native_source", "NativeJsonEnvelope", "body"):
        checked = _read_pdf_companion_export_events_adapter.validate_python(row[0], strict=True)
        return NativeJsonEnvelope(body=checked)


def read_pdf_companion_export_events(
    conn: Connection,
    *,
    task_id: TaskId,
    product_key: ProductKey,
    content_digest: ContentDigest,
    family: str,
    projection_context: PreparedRelease | None = None,
) -> tuple[NativeJsonEnvelope, ...]:
    _statement = prepare_read_pdf_companion_export_events(
        task_id=task_id,
        product_key=product_key,
        content_digest=content_digest,
        family=family,
        projection_context=projection_context,
    )
    _native_result = conn.execute(_statement)
    with native_result_scope("read_native_source", "NativeJsonEnvelope"):
        return tuple(materialize_read_pdf_companion_export_events(row) for row in _native_result)


READ_PDF_NATIVE_EVENTS_CONTRACT_DIGEST = (
    "f40d9bf273ebfc9bcdb96bb52cf46a39381fc45825a2d9258bb8f751bfd15b9d"
)


class _read_pdf_native_eventsRequest(OperationResult):
    task_id: Annotated[
        TaskId, Field(ge=TaskId(-9223372036854775808), le=TaskId(9223372036854775807))
    ]
    product_key: ProductKey
    content_digest: ContentDigest


_read_pdf_native_events_function = func.ops.read_pdf_native_events(
    bindparam("task_id", type_=BigInteger()),
    bindparam("product_key", type_=Text()),
    bindparam("content_digest", type_=Text()),
    type_=JSONB(),
)
_read_pdf_native_events_statement = select(_read_pdf_native_events_function.cast(Text()))


def prepare_read_pdf_native_events(
    *,
    task_id: TaskId,
    product_key: ProductKey,
    content_digest: ContentDigest,
    projection_context: PreparedRelease | None = None,
) -> Select[str]:
    _request = _read_pdf_native_eventsRequest(
        task_id=task_id,
        product_key=product_key,
        content_digest=content_digest,
    )
    if projection_context is not None:
        require_call_context(
            projection_context,
            "read_native_source",
            "read_pdf_native_events",
            READ_PDF_NATIVE_EVENTS_CONTRACT_DIGEST,
        )
    return _read_pdf_native_events_statement.params(
        **{
            "task_id": _request.task_id,
            "product_key": _request.product_key,
            "content_digest": _request.content_digest,
        }
    )


_read_pdf_native_events_adapter = TypeAdapter(str)


def materialize_read_pdf_native_events(row: tuple[str]) -> NativeJsonEnvelope:
    with native_result_scope("read_native_source", "NativeJsonEnvelope", "body"):
        checked = _read_pdf_native_events_adapter.validate_python(row[0], strict=True)
        return NativeJsonEnvelope(body=checked)


def read_pdf_native_events(
    conn: Connection,
    *,
    task_id: TaskId,
    product_key: ProductKey,
    content_digest: ContentDigest,
    projection_context: PreparedRelease | None = None,
) -> tuple[NativeJsonEnvelope, ...]:
    _statement = prepare_read_pdf_native_events(
        task_id=task_id,
        product_key=product_key,
        content_digest=content_digest,
        projection_context=projection_context,
    )
    _native_result = conn.execute(_statement)
    with native_result_scope("read_native_source", "NativeJsonEnvelope"):
        return tuple(materialize_read_pdf_native_events(row) for row in _native_result)


RECORD_INTEGRATED_SOURCE_CONTEXT_CONTRACT_DIGEST = (
    "d0e3a01ae3ec02e26bd8a251b657ce343b718c01166756688ece33e116e8b08e"
)


class _record_integrated_source_contextRequest(OperationResult):
    task_id: Annotated[
        TaskId, Field(ge=TaskId(-9223372036854775808), le=TaskId(9223372036854775807))
    ]
    product_key: ProductKey
    content_digest: ContentDigest
    pointers: tuple[str, ...]
    section: str
    membership: str
    row_budget: Annotated[int, Field(ge=-9223372036854775808, le=9223372036854775807)] | None


_record_integrated_source_context_function = func.ops.record_integrated_source_context(
    bindparam("task_id", type_=BigInteger()),
    bindparam("product_key", type_=Text()),
    bindparam("content_digest", type_=Text()),
    bindparam("pointers", type_=ARRAY(Text())),
    bindparam("section", type_=Text()),
    bindparam("membership", type_=Text()),
    bindparam("row_budget", type_=BigInteger()),
    type_=JSONB(),
)
_record_integrated_source_context_statement = select(
    _record_integrated_source_context_function.cast(Text())
)


def prepare_record_integrated_source_context(
    *,
    task_id: TaskId,
    product_key: ProductKey,
    content_digest: ContentDigest,
    pointers: tuple[str, ...],
    section: str,
    membership: str,
    row_budget: int | None,
    projection_context: PreparedRelease | None = None,
) -> Select[str]:
    _request = _record_integrated_source_contextRequest(
        task_id=task_id,
        product_key=product_key,
        content_digest=content_digest,
        pointers=pointers,
        section=section,
        membership=membership,
        row_budget=row_budget,
    )
    if projection_context is not None:
        require_call_context(
            projection_context,
            "read_native_source",
            "record_integrated_source_context",
            RECORD_INTEGRATED_SOURCE_CONTEXT_CONTRACT_DIGEST,
        )
    return _record_integrated_source_context_statement.params(
        **{
            "task_id": _request.task_id,
            "product_key": _request.product_key,
            "content_digest": _request.content_digest,
            "pointers": _request.pointers,
            "section": _request.section,
            "membership": _request.membership,
            "row_budget": _request.row_budget,
        }
    )


_record_integrated_source_context_adapter = TypeAdapter(str)


def materialize_record_integrated_source_context(row: tuple[str]) -> NativeJsonEnvelope:
    with native_result_scope("read_native_source", "NativeJsonEnvelope", "body"):
        checked = _record_integrated_source_context_adapter.validate_python(row[0], strict=True)
        return NativeJsonEnvelope(body=checked)


def record_integrated_source_context(
    conn: Connection,
    *,
    task_id: TaskId,
    product_key: ProductKey,
    content_digest: ContentDigest,
    pointers: tuple[str, ...],
    section: str,
    membership: str,
    row_budget: int | None,
    projection_context: PreparedRelease | None = None,
) -> NativeJsonEnvelope:
    _statement = prepare_record_integrated_source_context(
        task_id=task_id,
        product_key=product_key,
        content_digest=content_digest,
        pointers=pointers,
        section=section,
        membership=membership,
        row_budget=row_budget,
        projection_context=projection_context,
    )
    _native_result = conn.execute(_statement)
    with native_result_scope("read_native_source", "NativeJsonEnvelope"):
        row = _native_result.one()
        return materialize_record_integrated_source_context(row)


READ_PDF_SELECTED_SOURCE_EVENTS_CONTRACT_DIGEST = (
    "8c966c8223042811c0e6aae0269916945150e93005a01c5c56ffbb2aabde7a71"
)


class _read_pdf_selected_source_eventsRequest(OperationResult):
    project_id: ProjectId
    run_id: Annotated[RunId, Field(ge=RunId(-9223372036854775808), le=RunId(9223372036854775807))]
    selection_release_id: ReleaseId
    task_id: Annotated[
        TaskId, Field(ge=TaskId(-9223372036854775808), le=TaskId(9223372036854775807))
    ]
    product_key: ProductKey
    content_digest: ContentDigest
    section: str
    membership: str
    policy: str


_read_pdf_selected_source_events_function = func.ops.read_pdf_selected_source_events(
    bindparam("project_id", type_=Text()),
    bindparam("run_id", type_=BigInteger()),
    bindparam("selection_release_id", type_=Text()),
    bindparam("task_id", type_=BigInteger()),
    bindparam("product_key", type_=Text()),
    bindparam("content_digest", type_=Text()),
    bindparam("section", type_=Text()),
    bindparam("membership", type_=Text()),
    bindparam("policy", type_=Text()),
    type_=JSONB(),
)
_read_pdf_selected_source_events_statement = select(
    _read_pdf_selected_source_events_function.cast(Text())
)


def prepare_read_pdf_selected_source_events(
    *,
    project_id: ProjectId,
    run_id: RunId,
    selection_release_id: ReleaseId,
    task_id: TaskId,
    product_key: ProductKey,
    content_digest: ContentDigest,
    section: str,
    membership: str,
    policy: str,
    projection_context: PreparedRelease | None = None,
) -> Select[str]:
    _request = _read_pdf_selected_source_eventsRequest(
        project_id=project_id,
        run_id=run_id,
        selection_release_id=selection_release_id,
        task_id=task_id,
        product_key=product_key,
        content_digest=content_digest,
        section=section,
        membership=membership,
        policy=policy,
    )
    if projection_context is not None:
        require_call_context(
            projection_context,
            "read_native_source",
            "read_pdf_selected_source_events",
            READ_PDF_SELECTED_SOURCE_EVENTS_CONTRACT_DIGEST,
        )
    return _read_pdf_selected_source_events_statement.params(
        **{
            "project_id": _request.project_id,
            "run_id": _request.run_id,
            "selection_release_id": _request.selection_release_id,
            "task_id": _request.task_id,
            "product_key": _request.product_key,
            "content_digest": _request.content_digest,
            "section": _request.section,
            "membership": _request.membership,
            "policy": _request.policy,
        }
    )


_read_pdf_selected_source_events_adapter = TypeAdapter(str)


def materialize_read_pdf_selected_source_events(row: tuple[str]) -> NativeJsonEnvelope:
    with native_result_scope("read_native_source", "NativeJsonEnvelope", "body"):
        checked = _read_pdf_selected_source_events_adapter.validate_python(row[0], strict=True)
        return NativeJsonEnvelope(body=checked)


def read_pdf_selected_source_events(
    conn: Connection,
    *,
    project_id: ProjectId,
    run_id: RunId,
    selection_release_id: ReleaseId,
    task_id: TaskId,
    product_key: ProductKey,
    content_digest: ContentDigest,
    section: str,
    membership: str,
    policy: str,
    projection_context: PreparedRelease | None = None,
) -> tuple[NativeJsonEnvelope, ...]:
    _statement = prepare_read_pdf_selected_source_events(
        project_id=project_id,
        run_id=run_id,
        selection_release_id=selection_release_id,
        task_id=task_id,
        product_key=product_key,
        content_digest=content_digest,
        section=section,
        membership=membership,
        policy=policy,
        projection_context=projection_context,
    )
    _native_result = conn.execute(_statement)
    with native_result_scope("read_native_source", "NativeJsonEnvelope"):
        return tuple(materialize_read_pdf_selected_source_events(row) for row in _native_result)


CAPTURE_NATIVE_SOURCE_FRAME_CONTRACT_DIGEST = (
    "5836a4f3811757826d326515c2be5d86b8d62f04e85b1e7d27f9216f7d29562f"
)


class _capture_native_source_frameRequest(OperationResult):
    task_id: Annotated[
        TaskId, Field(ge=TaskId(-9223372036854775808), le=TaskId(9223372036854775807))
    ]
    packet_hash: str
    frame: JsonValue


_capture_native_source_frame_function = func.ops.capture_native_source_frame(
    bindparam("task_id", type_=BigInteger()),
    bindparam("packet_hash", type_=Text()),
    bindparam("frame", type_=JSONB()),
)
_capture_native_source_frame_statement = select(_capture_native_source_frame_function)


def prepare_capture_native_source_frame(
    *,
    task_id: TaskId,
    packet_hash: str,
    frame: JsonValue,
    projection_context: PreparedRelease | None = None,
) -> Select[None]:
    _request = _capture_native_source_frameRequest(
        task_id=task_id,
        packet_hash=packet_hash,
        frame=frame,
    )
    if projection_context is not None:
        require_call_context(
            projection_context,
            "capture_native_source_frame",
            "capture_native_source_frame",
            CAPTURE_NATIVE_SOURCE_FRAME_CONTRACT_DIGEST,
        )
    return _capture_native_source_frame_statement.params(
        **{
            "task_id": _request.task_id,
            "packet_hash": _request.packet_hash,
            "frame": _request.frame,
        }
    )


def capture_native_source_frame(
    conn: Connection,
    *,
    task_id: TaskId,
    packet_hash: str,
    frame: JsonValue,
    projection_context: PreparedRelease | None = None,
) -> None:
    _statement = prepare_capture_native_source_frame(
        task_id=task_id,
        packet_hash=packet_hash,
        frame=frame,
        projection_context=projection_context,
    )
    _native_result = conn.execute(_statement)
    with native_result_scope("capture_native_source_frame", "capture_native_source_frame"):
        _native_result.scalar_one()
    return None


PUBLISH_PDF_REGION_ARTIFACT_CONTRACT_DIGEST = (
    "df6e6e61d570ad62af4a8db023050d5f6b2be3bea1d33f4e4f27d46f4b73b363"
)


class _publish_pdf_region_artifactRequest(OperationResult):
    task_id: Annotated[
        TaskId, Field(ge=TaskId(-9223372036854775808), le=TaskId(9223372036854775807))
    ]
    attempt: Annotated[
        TaskAttempt,
        Field(ge=TaskAttempt(-9223372036854775808), le=TaskAttempt(9223372036854775807)),
    ]
    holder: str
    selection: JsonValue
    recipe: bytes
    content: bytes


_publish_pdf_region_artifact_function = func.ops.publish_pdf_region_artifact(
    bindparam("task_id", type_=BigInteger()),
    bindparam("attempt", type_=BigInteger()),
    bindparam("holder", type_=Text()),
    bindparam("selection", type_=JSONB()),
    bindparam("recipe", type_=BYTEA()),
    bindparam("content", type_=BYTEA()),
    type_=Text(),
)
_publish_pdf_region_artifact_statement = select(_publish_pdf_region_artifact_function)


def prepare_publish_pdf_region_artifact(
    *,
    task_id: TaskId,
    attempt: TaskAttempt,
    holder: str,
    selection: JsonValue,
    recipe: bytes,
    content: bytes,
    projection_context: PreparedRelease | None = None,
) -> Select[str]:
    _request = _publish_pdf_region_artifactRequest(
        task_id=task_id,
        attempt=attempt,
        holder=holder,
        selection=selection,
        recipe=recipe,
        content=content,
    )
    if projection_context is not None:
        require_call_context(
            projection_context,
            "publish_pdf_region_artifact",
            "publish_pdf_region_artifact",
            PUBLISH_PDF_REGION_ARTIFACT_CONTRACT_DIGEST,
        )
    return _publish_pdf_region_artifact_statement.params(
        **{
            "task_id": _request.task_id,
            "attempt": _request.attempt,
            "holder": _request.holder,
            "selection": _request.selection,
            "recipe": _request.recipe,
            "content": _request.content,
        }
    )


_publish_pdf_region_artifact_adapter = TypeAdapter(str)


def materialize_publish_pdf_region_artifact(row: tuple[str]) -> str:
    with native_result_scope(
        "publish_pdf_region_artifact", "publish_pdf_region_artifact", "digest"
    ):
        checked = _publish_pdf_region_artifact_adapter.validate_python(row[0], strict=True)
        return checked


def publish_pdf_region_artifact(
    conn: Connection,
    *,
    task_id: TaskId,
    attempt: TaskAttempt,
    holder: str,
    selection: JsonValue,
    recipe: bytes,
    content: bytes,
    projection_context: PreparedRelease | None = None,
) -> str:
    _statement = prepare_publish_pdf_region_artifact(
        task_id=task_id,
        attempt=attempt,
        holder=holder,
        selection=selection,
        recipe=recipe,
        content=content,
        projection_context=projection_context,
    )
    _native_result = conn.execute(_statement)
    with native_result_scope("publish_pdf_region_artifact", "publish_pdf_region_artifact"):
        row = _native_result.one()
        return materialize_publish_pdf_region_artifact(row)


PUBLISH_PDF_OBSERVATION_CONTRACT_DIGEST = (
    "f2835d980a95f69355dcd74b6fbaeaa0e33b3c1db4cf6a8bbdf2921bc47ba835"
)


class _publish_pdf_observationRequest(OperationResult):
    task_id: Annotated[
        TaskId, Field(ge=TaskId(-9223372036854775808), le=TaskId(9223372036854775807))
    ]
    attempt: Annotated[
        TaskAttempt,
        Field(ge=TaskAttempt(-9223372036854775808), le=TaskAttempt(9223372036854775807)),
    ]
    holder: str
    contract_digest: str
    payload: bytes
    artifacts: tuple[bytes, ...]


_publish_pdf_observation_function = func.ops.publish_pdf_observation(
    bindparam("task_id", type_=BigInteger()),
    bindparam("attempt", type_=BigInteger()),
    bindparam("holder", type_=Text()),
    bindparam("contract_digest", type_=Text()),
    bindparam("payload", type_=BYTEA()),
    bindparam("artifacts", type_=ARRAY(BYTEA())),
    type_=Text(),
)
_publish_pdf_observation_statement = select(_publish_pdf_observation_function)


def prepare_publish_pdf_observation(
    *,
    task_id: TaskId,
    attempt: TaskAttempt,
    holder: str,
    contract_digest: str,
    payload: bytes,
    artifacts: tuple[bytes, ...],
    projection_context: PreparedRelease | None = None,
) -> Select[str]:
    _request = _publish_pdf_observationRequest(
        task_id=task_id,
        attempt=attempt,
        holder=holder,
        contract_digest=contract_digest,
        payload=payload,
        artifacts=artifacts,
    )
    if projection_context is not None:
        require_call_context(
            projection_context,
            "publish_pdf_observation",
            "publish_pdf_observation",
            PUBLISH_PDF_OBSERVATION_CONTRACT_DIGEST,
        )
    return _publish_pdf_observation_statement.params(
        **{
            "task_id": _request.task_id,
            "attempt": _request.attempt,
            "holder": _request.holder,
            "contract_digest": _request.contract_digest,
            "payload": _request.payload,
            "artifacts": _request.artifacts,
        }
    )


_publish_pdf_observation_adapter = TypeAdapter(str)


def materialize_publish_pdf_observation(row: tuple[str]) -> str:
    with native_result_scope(
        "publish_pdf_observation", "publish_pdf_observation", "content_digest"
    ):
        checked = _publish_pdf_observation_adapter.validate_python(row[0], strict=True)
        return checked


def publish_pdf_observation(
    conn: Connection,
    *,
    task_id: TaskId,
    attempt: TaskAttempt,
    holder: str,
    contract_digest: str,
    payload: bytes,
    artifacts: tuple[bytes, ...],
    projection_context: PreparedRelease | None = None,
) -> str:
    _statement = prepare_publish_pdf_observation(
        task_id=task_id,
        attempt=attempt,
        holder=holder,
        contract_digest=contract_digest,
        payload=payload,
        artifacts=artifacts,
        projection_context=projection_context,
    )
    _native_result = conn.execute(_statement)
    with native_result_scope("publish_pdf_observation", "publish_pdf_observation"):
        row = _native_result.one()
        return materialize_publish_pdf_observation(row)


READ_PDF_PUBLISHED_REVISION_CONTRACT_DIGEST = (
    "58cbd55cdc1359113ed8ef050a223842e0cde1f42b2305659563d47453c5dd13"
)


class PdfPublishedRevision(NativeRowResult):
    build_id: str
    task_id: int
    product_key: str
    logical_digest: str
    release_id: str
    source_digest: str
    schema_digest: str
    recipe_digest: str
    frozen_digest: str
    kind: Literal["integrated", "native"]


class _read_pdf_published_revisionRequest(OperationResult):
    task_id: Annotated[
        TaskId, Field(ge=TaskId(-9223372036854775808), le=TaskId(9223372036854775807))
    ]
    product_key: str
    logical_digest: str


_read_pdf_published_revision_function = func.ops.read_pdf_published_revision(
    bindparam("task_id", type_=BigInteger()),
    bindparam("product_key", type_=Text()),
    bindparam("logical_digest", type_=Text()),
).table_valued(
    column("build_id", Text()),
    column("task_id", BigInteger()),
    column("product_key", Text()),
    column("logical_digest", Text()),
    column("release_id", Text()),
    column("source_digest", Text()),
    column("schema_digest", Text()),
    column("recipe_digest", Text()),
    column("frozen_digest", Text()),
    column("kind", Text()),
)


class _read_pdf_published_revisionColumns(Protocol):
    build_id: Column[str]
    task_id: Column[int]
    product_key: Column[str]
    logical_digest: Column[str]
    release_id: Column[str]
    source_digest: Column[str]
    schema_digest: Column[str]
    recipe_digest: Column[str]
    frozen_digest: Column[str]
    kind: Column[str]


_read_pdf_published_revision_columns = cast(
    _read_pdf_published_revisionColumns, _read_pdf_published_revision_function.c
)
_read_pdf_published_revision_statement = select(
    _read_pdf_published_revision_columns.build_id,
    _read_pdf_published_revision_columns.task_id,
    _read_pdf_published_revision_columns.product_key,
    _read_pdf_published_revision_columns.logical_digest,
    _read_pdf_published_revision_columns.release_id,
    _read_pdf_published_revision_columns.source_digest,
    _read_pdf_published_revision_columns.schema_digest,
    _read_pdf_published_revision_columns.recipe_digest,
    _read_pdf_published_revision_columns.frozen_digest,
    _read_pdf_published_revision_columns.kind,
)


def _read_pdf_published_revision_result(
    row: tuple[str, int, str, str, str, str, str, str, str, str],
) -> PdfPublishedRevision:
    with native_result_scope("read_pdf_product", "PdfPublishedRevision"):
        return PdfPublishedRevision(
            build_id=row[0],
            task_id=row[1],
            product_key=row[2],
            logical_digest=row[3],
            release_id=row[4],
            source_digest=row[5],
            schema_digest=row[6],
            recipe_digest=row[7],
            frozen_digest=row[8],
            kind=cast(Literal["integrated", "native"], row[9]),
        )


def prepare_read_pdf_published_revision(
    *,
    task_id: TaskId,
    product_key: str,
    logical_digest: str,
    projection_context: PreparedRelease | None = None,
) -> Select[str, int, str, str, str, str, str, str, str, str]:
    _request = _read_pdf_published_revisionRequest(
        task_id=task_id,
        product_key=product_key,
        logical_digest=logical_digest,
    )
    if projection_context is not None:
        require_call_context(
            projection_context,
            "read_pdf_product",
            "read_pdf_published_revision",
            READ_PDF_PUBLISHED_REVISION_CONTRACT_DIGEST,
        )
    return _read_pdf_published_revision_statement.params(
        **{
            "task_id": _request.task_id,
            "product_key": _request.product_key,
            "logical_digest": _request.logical_digest,
        }
    )


materialize_read_pdf_published_revision = _read_pdf_published_revision_result


def read_pdf_published_revision(
    conn: Connection,
    *,
    task_id: TaskId,
    product_key: str,
    logical_digest: str,
    projection_context: PreparedRelease | None = None,
) -> PdfPublishedRevision | None:
    _statement = prepare_read_pdf_published_revision(
        task_id=task_id,
        product_key=product_key,
        logical_digest=logical_digest,
        projection_context=projection_context,
    )
    _native_result = conn.execute(_statement)
    with native_result_scope("read_pdf_product", "PdfPublishedRevision"):
        row = _native_result.one_or_none()
        return None if row is None else _read_pdf_published_revision_result(row)


READ_PDF_PUBLISHED_VALIDATION_CONTRACT_DIGEST = (
    "776cc3a468e57b8ded2353f0358bb5c676c8fdd89e6c20068197fe4da260cd42"
)


class PdfBuildValidation(NativeRowResult):
    build_id: str
    frozen_digest: str
    logical_digest: str
    contract_digest: str
    native_callbacks: bool
    native_contract_digest: str


class _read_pdf_published_validationRequest(OperationResult):
    task_id: Annotated[
        TaskId, Field(ge=TaskId(-9223372036854775808), le=TaskId(9223372036854775807))
    ]
    product_key: ProductKey
    content_digest: ContentDigest


_read_pdf_published_validation_function = func.ops.read_pdf_published_validation(
    bindparam("task_id", type_=BigInteger()),
    bindparam("product_key", type_=Text()),
    bindparam("content_digest", type_=Text()),
).table_valued(
    column("build_id", Text()),
    column("frozen_digest", Text()),
    column("logical_digest", Text()),
    column("contract_digest", Text()),
    column("native_callbacks", Boolean()),
    column("native_contract_digest", Text()),
)


class _read_pdf_published_validationColumns(Protocol):
    build_id: Column[str]
    frozen_digest: Column[str]
    logical_digest: Column[str]
    contract_digest: Column[str]
    native_callbacks: Column[bool]
    native_contract_digest: Column[str]


_read_pdf_published_validation_columns = cast(
    _read_pdf_published_validationColumns, _read_pdf_published_validation_function.c
)
_read_pdf_published_validation_statement = select(
    _read_pdf_published_validation_columns.build_id,
    _read_pdf_published_validation_columns.frozen_digest,
    _read_pdf_published_validation_columns.logical_digest,
    _read_pdf_published_validation_columns.contract_digest,
    _read_pdf_published_validation_columns.native_callbacks,
    _read_pdf_published_validation_columns.native_contract_digest,
)


def _read_pdf_published_validation_result(
    row: tuple[str, str, str, str, bool, str],
) -> PdfBuildValidation:
    with native_result_scope("read_pdf_product", "PdfBuildValidation"):
        return PdfBuildValidation(
            build_id=row[0],
            frozen_digest=row[1],
            logical_digest=row[2],
            contract_digest=row[3],
            native_callbacks=row[4],
            native_contract_digest=row[5],
        )


def prepare_read_pdf_published_validation(
    *,
    task_id: TaskId,
    product_key: ProductKey,
    content_digest: ContentDigest,
    projection_context: PreparedRelease | None = None,
) -> Select[str, str, str, str, bool, str]:
    _request = _read_pdf_published_validationRequest(
        task_id=task_id,
        product_key=product_key,
        content_digest=content_digest,
    )
    if projection_context is not None:
        require_call_context(
            projection_context,
            "read_pdf_product",
            "read_pdf_published_validation",
            READ_PDF_PUBLISHED_VALIDATION_CONTRACT_DIGEST,
        )
    return _read_pdf_published_validation_statement.params(
        **{
            "task_id": _request.task_id,
            "product_key": _request.product_key,
            "content_digest": _request.content_digest,
        }
    )


materialize_read_pdf_published_validation = _read_pdf_published_validation_result


def read_pdf_published_validation(
    conn: Connection,
    *,
    task_id: TaskId,
    product_key: ProductKey,
    content_digest: ContentDigest,
    projection_context: PreparedRelease | None = None,
) -> PdfBuildValidation | None:
    _statement = prepare_read_pdf_published_validation(
        task_id=task_id,
        product_key=product_key,
        content_digest=content_digest,
        projection_context=projection_context,
    )
    _native_result = conn.execute(_statement)
    with native_result_scope("read_pdf_product", "PdfBuildValidation"):
        row = _native_result.one_or_none()
        return None if row is None else _read_pdf_published_validation_result(row)


FREEZE_PDF_BUILD_CONTRACT_DIGEST = (
    "59ce0ff1e03371a283e004338d75d7a09806b34be388310023fce81da72c7801"
)


class _freeze_pdf_buildRequest(OperationResult):
    build_id: str
    task_id: Annotated[
        TaskId, Field(ge=TaskId(-9223372036854775808), le=TaskId(9223372036854775807))
    ]
    attempt: Annotated[
        TaskAttempt,
        Field(ge=TaskAttempt(-9223372036854775808), le=TaskAttempt(9223372036854775807)),
    ]
    holder: str
    kind: PdfFrozenBuildKind


_freeze_pdf_build_function = func.ops.freeze_pdf_build(
    bindparam("build_id", type_=Text()),
    bindparam("task_id", type_=BigInteger()),
    bindparam("attempt", type_=BigInteger()),
    bindparam("holder", type_=Text()),
    bindparam("kind", type_=Text()),
    type_=Text(),
)
_freeze_pdf_build_statement = select(_freeze_pdf_build_function)


def prepare_freeze_pdf_build(
    *,
    build_id: str,
    task_id: TaskId,
    attempt: TaskAttempt,
    holder: str,
    kind: PdfFrozenBuildKind,
    projection_context: PreparedRelease | None = None,
) -> Select[str]:
    _request = _freeze_pdf_buildRequest(
        build_id=build_id,
        task_id=task_id,
        attempt=attempt,
        holder=holder,
        kind=kind,
    )
    if projection_context is not None:
        require_call_context(
            projection_context,
            "freeze_pdf_build",
            "freeze_pdf_build",
            FREEZE_PDF_BUILD_CONTRACT_DIGEST,
        )
    return _freeze_pdf_build_statement.params(
        **{
            "build_id": _request.build_id,
            "task_id": _request.task_id,
            "attempt": _request.attempt,
            "holder": _request.holder,
            "kind": _request.kind,
        }
    )


_freeze_pdf_build_adapter = TypeAdapter(str)


def materialize_freeze_pdf_build(row: tuple[str]) -> str:
    with native_result_scope("freeze_pdf_build", "freeze_pdf_build", "frozen_digest"):
        checked = _freeze_pdf_build_adapter.validate_python(row[0], strict=True)
        return checked


def freeze_pdf_build(
    conn: Connection,
    *,
    build_id: str,
    task_id: TaskId,
    attempt: TaskAttempt,
    holder: str,
    kind: PdfFrozenBuildKind,
    projection_context: PreparedRelease | None = None,
) -> str:
    _statement = prepare_freeze_pdf_build(
        build_id=build_id,
        task_id=task_id,
        attempt=attempt,
        holder=holder,
        kind=kind,
        projection_context=projection_context,
    )
    _native_result = conn.execute(_statement)
    with native_result_scope("freeze_pdf_build", "freeze_pdf_build"):
        row = _native_result.one()
        return materialize_freeze_pdf_build(row)


PREPARE_PDF_BUILD_CONTRACT_DIGEST = (
    "278f091191296a68c65b7e42e81dc3f2abe0f6d9d9a2f4846388d5851815228d"
)


class _prepare_pdf_buildRequest(OperationResult):
    build_id: str
    task_id: Annotated[
        TaskId, Field(ge=TaskId(-9223372036854775808), le=TaskId(9223372036854775807))
    ]
    attempt: Annotated[
        TaskAttempt,
        Field(ge=TaskAttempt(-9223372036854775808), le=TaskAttempt(9223372036854775807)),
    ]
    holder: str
    frozen_digest: str


_prepare_pdf_build_function = func.ops.prepare_pdf_build(
    bindparam("build_id", type_=Text()),
    bindparam("task_id", type_=BigInteger()),
    bindparam("attempt", type_=BigInteger()),
    bindparam("holder", type_=Text()),
    bindparam("frozen_digest", type_=Text()),
)
_prepare_pdf_build_statement = select(_prepare_pdf_build_function)


def prepare_prepare_pdf_build(
    *,
    build_id: str,
    task_id: TaskId,
    attempt: TaskAttempt,
    holder: str,
    frozen_digest: str,
    projection_context: PreparedRelease | None = None,
) -> Select[None]:
    _request = _prepare_pdf_buildRequest(
        build_id=build_id,
        task_id=task_id,
        attempt=attempt,
        holder=holder,
        frozen_digest=frozen_digest,
    )
    if projection_context is not None:
        require_call_context(
            projection_context,
            "prepare_pdf_build",
            "prepare_pdf_build",
            PREPARE_PDF_BUILD_CONTRACT_DIGEST,
        )
    return _prepare_pdf_build_statement.params(
        **{
            "build_id": _request.build_id,
            "task_id": _request.task_id,
            "attempt": _request.attempt,
            "holder": _request.holder,
            "frozen_digest": _request.frozen_digest,
        }
    )


def prepare_pdf_build(
    conn: Connection,
    *,
    build_id: str,
    task_id: TaskId,
    attempt: TaskAttempt,
    holder: str,
    frozen_digest: str,
    projection_context: PreparedRelease | None = None,
) -> None:
    _statement = prepare_prepare_pdf_build(
        build_id=build_id,
        task_id=task_id,
        attempt=attempt,
        holder=holder,
        frozen_digest=frozen_digest,
        projection_context=projection_context,
    )
    _native_result = conn.execute(_statement)
    with native_result_scope("prepare_pdf_build", "prepare_pdf_build"):
        _native_result.scalar_one()
    return None


LOOKUP_PDF_VALIDATION_CONTRACT_DIGEST = (
    "0c792cf1065c3c6715c035aeff09e81bb1369bf28a1324e156450faff948a06a"
)


class _lookup_pdf_validationRequest(OperationResult):
    build_id: str
    task_id: Annotated[
        TaskId, Field(ge=TaskId(-9223372036854775808), le=TaskId(9223372036854775807))
    ]
    attempt: Annotated[
        TaskAttempt,
        Field(ge=TaskAttempt(-9223372036854775808), le=TaskAttempt(9223372036854775807)),
    ]
    holder: str
    frozen_digest: str


_lookup_pdf_validation_function = func.ops.lookup_pdf_validation(
    bindparam("build_id", type_=Text()),
    bindparam("task_id", type_=BigInteger()),
    bindparam("attempt", type_=BigInteger()),
    bindparam("holder", type_=Text()),
    bindparam("frozen_digest", type_=Text()),
).table_valued(
    column("build_id", Text()),
    column("frozen_digest", Text()),
    column("logical_digest", Text()),
    column("contract_digest", Text()),
    column("native_callbacks", Boolean()),
    column("native_contract_digest", Text()),
)


class _lookup_pdf_validationColumns(Protocol):
    build_id: Column[str]
    frozen_digest: Column[str]
    logical_digest: Column[str]
    contract_digest: Column[str]
    native_callbacks: Column[bool]
    native_contract_digest: Column[str]


_lookup_pdf_validation_columns = cast(
    _lookup_pdf_validationColumns, _lookup_pdf_validation_function.c
)
_lookup_pdf_validation_statement = select(
    _lookup_pdf_validation_columns.build_id,
    _lookup_pdf_validation_columns.frozen_digest,
    _lookup_pdf_validation_columns.logical_digest,
    _lookup_pdf_validation_columns.contract_digest,
    _lookup_pdf_validation_columns.native_callbacks,
    _lookup_pdf_validation_columns.native_contract_digest,
)


def _lookup_pdf_validation_result(row: tuple[str, str, str, str, bool, str]) -> PdfBuildValidation:
    with native_result_scope("validate_pdf_build", "PdfBuildValidation"):
        return PdfBuildValidation(
            build_id=row[0],
            frozen_digest=row[1],
            logical_digest=row[2],
            contract_digest=row[3],
            native_callbacks=row[4],
            native_contract_digest=row[5],
        )


def prepare_lookup_pdf_validation(
    *,
    build_id: str,
    task_id: TaskId,
    attempt: TaskAttempt,
    holder: str,
    frozen_digest: str,
    projection_context: PreparedRelease | None = None,
) -> Select[str, str, str, str, bool, str]:
    _request = _lookup_pdf_validationRequest(
        build_id=build_id,
        task_id=task_id,
        attempt=attempt,
        holder=holder,
        frozen_digest=frozen_digest,
    )
    if projection_context is not None:
        require_call_context(
            projection_context,
            "validate_pdf_build",
            "lookup_pdf_validation",
            LOOKUP_PDF_VALIDATION_CONTRACT_DIGEST,
        )
    return _lookup_pdf_validation_statement.params(
        **{
            "build_id": _request.build_id,
            "task_id": _request.task_id,
            "attempt": _request.attempt,
            "holder": _request.holder,
            "frozen_digest": _request.frozen_digest,
        }
    )


materialize_lookup_pdf_validation = _lookup_pdf_validation_result


def lookup_pdf_validation(
    conn: Connection,
    *,
    build_id: str,
    task_id: TaskId,
    attempt: TaskAttempt,
    holder: str,
    frozen_digest: str,
    projection_context: PreparedRelease | None = None,
) -> PdfBuildValidation | None:
    _statement = prepare_lookup_pdf_validation(
        build_id=build_id,
        task_id=task_id,
        attempt=attempt,
        holder=holder,
        frozen_digest=frozen_digest,
        projection_context=projection_context,
    )
    _native_result = conn.execute(_statement)
    with native_result_scope("validate_pdf_build", "PdfBuildValidation"):
        row = _native_result.one_or_none()
        return None if row is None else _lookup_pdf_validation_result(row)


RECORD_PDF_NATIVE_VALIDATION_CONTRACT_DIGEST = (
    "87c265c727815829c2f99a28f36238d7d7acb6ca851e44c53b176f78fe095e7d"
)


class _record_pdf_native_validationRequest(OperationResult):
    build_id: str
    task_id: Annotated[
        TaskId, Field(ge=TaskId(-9223372036854775808), le=TaskId(9223372036854775807))
    ]
    attempt: Annotated[
        TaskAttempt,
        Field(ge=TaskAttempt(-9223372036854775808), le=TaskAttempt(9223372036854775807)),
    ]
    holder: str
    frozen_digest: str
    passed: bool


_record_pdf_native_validation_function = func.ops.record_pdf_native_validation(
    bindparam("build_id", type_=Text()),
    bindparam("task_id", type_=BigInteger()),
    bindparam("attempt", type_=BigInteger()),
    bindparam("holder", type_=Text()),
    bindparam("frozen_digest", type_=Text()),
    bindparam("passed", type_=Boolean()),
)
_record_pdf_native_validation_statement = select(_record_pdf_native_validation_function)


def prepare_record_pdf_native_validation(
    *,
    build_id: str,
    task_id: TaskId,
    attempt: TaskAttempt,
    holder: str,
    frozen_digest: str,
    passed: bool,
    projection_context: PreparedRelease | None = None,
) -> Select[None]:
    _request = _record_pdf_native_validationRequest(
        build_id=build_id,
        task_id=task_id,
        attempt=attempt,
        holder=holder,
        frozen_digest=frozen_digest,
        passed=passed,
    )
    if projection_context is not None:
        require_call_context(
            projection_context,
            "validate_pdf_build",
            "record_pdf_native_validation",
            RECORD_PDF_NATIVE_VALIDATION_CONTRACT_DIGEST,
        )
    return _record_pdf_native_validation_statement.params(
        **{
            "build_id": _request.build_id,
            "task_id": _request.task_id,
            "attempt": _request.attempt,
            "holder": _request.holder,
            "frozen_digest": _request.frozen_digest,
            "passed": _request.passed,
        }
    )


def record_pdf_native_validation(
    conn: Connection,
    *,
    build_id: str,
    task_id: TaskId,
    attempt: TaskAttempt,
    holder: str,
    frozen_digest: str,
    passed: bool,
    projection_context: PreparedRelease | None = None,
) -> None:
    _statement = prepare_record_pdf_native_validation(
        build_id=build_id,
        task_id=task_id,
        attempt=attempt,
        holder=holder,
        frozen_digest=frozen_digest,
        passed=passed,
        projection_context=projection_context,
    )
    _native_result = conn.execute(_statement)
    with native_result_scope("validate_pdf_build", "record_pdf_native_validation"):
        _native_result.scalar_one()
    return None


CHECK_PDF_BUILD_CONTRACT_DIGEST = "c34dfe255fe150deed01f3af6b88b1a6fa42462c0b7283feba9d07b13aade11d"


class _check_pdf_buildRequest(OperationResult):
    build_id: str
    task_id: Annotated[
        TaskId, Field(ge=TaskId(-9223372036854775808), le=TaskId(9223372036854775807))
    ]
    attempt: Annotated[
        TaskAttempt,
        Field(ge=TaskAttempt(-9223372036854775808), le=TaskAttempt(9223372036854775807)),
    ]
    holder: str
    frozen_digest: str
    check_name: str


_check_pdf_build_function = func.ops.check_pdf_build(
    bindparam("build_id", type_=Text()),
    bindparam("task_id", type_=BigInteger()),
    bindparam("attempt", type_=BigInteger()),
    bindparam("holder", type_=Text()),
    bindparam("frozen_digest", type_=Text()),
    bindparam("check_name", type_=Text()),
)
_check_pdf_build_statement = select(_check_pdf_build_function)


def prepare_check_pdf_build(
    *,
    build_id: str,
    task_id: TaskId,
    attempt: TaskAttempt,
    holder: str,
    frozen_digest: str,
    check_name: str,
    projection_context: PreparedRelease | None = None,
) -> Select[None]:
    _request = _check_pdf_buildRequest(
        build_id=build_id,
        task_id=task_id,
        attempt=attempt,
        holder=holder,
        frozen_digest=frozen_digest,
        check_name=check_name,
    )
    if projection_context is not None:
        require_call_context(
            projection_context,
            "validate_pdf_build",
            "check_pdf_build",
            CHECK_PDF_BUILD_CONTRACT_DIGEST,
        )
    return _check_pdf_build_statement.params(
        **{
            "build_id": _request.build_id,
            "task_id": _request.task_id,
            "attempt": _request.attempt,
            "holder": _request.holder,
            "frozen_digest": _request.frozen_digest,
            "check_name": _request.check_name,
        }
    )


def check_pdf_build(
    conn: Connection,
    *,
    build_id: str,
    task_id: TaskId,
    attempt: TaskAttempt,
    holder: str,
    frozen_digest: str,
    check_name: str,
    projection_context: PreparedRelease | None = None,
) -> None:
    _statement = prepare_check_pdf_build(
        build_id=build_id,
        task_id=task_id,
        attempt=attempt,
        holder=holder,
        frozen_digest=frozen_digest,
        check_name=check_name,
        projection_context=projection_context,
    )
    _native_result = conn.execute(_statement)
    with native_result_scope("validate_pdf_build", "check_pdf_build"):
        _native_result.scalar_one()
    return None


ADOPT_PDF_ACCESS_BATCH_CONTRACT_DIGEST = (
    "38ea95cf1755f4f4a21aaddb02ceac6fa0aff43d38fe3889c3afbc6c827e5007"
)


class _adopt_pdf_access_batchRequest(OperationResult):
    build_id: str
    task_id: Annotated[
        TaskId, Field(ge=TaskId(-9223372036854775808), le=TaskId(9223372036854775807))
    ]
    attempt: Annotated[
        TaskAttempt,
        Field(ge=TaskAttempt(-9223372036854775808), le=TaskAttempt(9223372036854775807)),
    ]
    holder: str
    frozen_digest: str
    rows: JsonValue


_adopt_pdf_access_batch_function = func.ops.adopt_pdf_access_batch(
    bindparam("build_id", type_=Text()),
    bindparam("task_id", type_=BigInteger()),
    bindparam("attempt", type_=BigInteger()),
    bindparam("holder", type_=Text()),
    bindparam("frozen_digest", type_=Text()),
    bindparam("rows", type_=JSONB()),
)
_adopt_pdf_access_batch_statement = select(_adopt_pdf_access_batch_function)


def prepare_adopt_pdf_access_batch(
    *,
    build_id: str,
    task_id: TaskId,
    attempt: TaskAttempt,
    holder: str,
    frozen_digest: str,
    rows: JsonValue,
    projection_context: PreparedRelease | None = None,
) -> Select[None]:
    _request = _adopt_pdf_access_batchRequest(
        build_id=build_id,
        task_id=task_id,
        attempt=attempt,
        holder=holder,
        frozen_digest=frozen_digest,
        rows=rows,
    )
    if projection_context is not None:
        require_call_context(
            projection_context,
            "validate_pdf_build",
            "adopt_pdf_access_batch",
            ADOPT_PDF_ACCESS_BATCH_CONTRACT_DIGEST,
        )
    return _adopt_pdf_access_batch_statement.params(
        **{
            "build_id": _request.build_id,
            "task_id": _request.task_id,
            "attempt": _request.attempt,
            "holder": _request.holder,
            "frozen_digest": _request.frozen_digest,
            "rows": _request.rows,
        }
    )


def adopt_pdf_access_batch(
    conn: Connection,
    *,
    build_id: str,
    task_id: TaskId,
    attempt: TaskAttempt,
    holder: str,
    frozen_digest: str,
    rows: JsonValue,
    projection_context: PreparedRelease | None = None,
) -> None:
    _statement = prepare_adopt_pdf_access_batch(
        build_id=build_id,
        task_id=task_id,
        attempt=attempt,
        holder=holder,
        frozen_digest=frozen_digest,
        rows=rows,
        projection_context=projection_context,
    )
    _native_result = conn.execute(_statement)
    with native_result_scope("validate_pdf_build", "adopt_pdf_access_batch"):
        _native_result.scalar_one()
    return None


VALIDATE_PDF_BUILD_CONTRACT_DIGEST = (
    "5fa576ca0f4258cbd7a8325a3ec8334bf77fb3c967c75db034776ed8e6d7707c"
)


class _validate_pdf_buildRequest(OperationResult):
    build_id: str
    task_id: Annotated[
        TaskId, Field(ge=TaskId(-9223372036854775808), le=TaskId(9223372036854775807))
    ]
    attempt: Annotated[
        TaskAttempt,
        Field(ge=TaskAttempt(-9223372036854775808), le=TaskAttempt(9223372036854775807)),
    ]
    holder: str
    frozen_digest: str


_validate_pdf_build_function = func.ops.validate_pdf_build(
    bindparam("build_id", type_=Text()),
    bindparam("task_id", type_=BigInteger()),
    bindparam("attempt", type_=BigInteger()),
    bindparam("holder", type_=Text()),
    bindparam("frozen_digest", type_=Text()),
).table_valued(
    column("build_id", Text()),
    column("frozen_digest", Text()),
    column("logical_digest", Text()),
    column("contract_digest", Text()),
    column("native_callbacks", Boolean()),
    column("native_contract_digest", Text()),
)


class _validate_pdf_buildColumns(Protocol):
    build_id: Column[str]
    frozen_digest: Column[str]
    logical_digest: Column[str]
    contract_digest: Column[str]
    native_callbacks: Column[bool]
    native_contract_digest: Column[str]


_validate_pdf_build_columns = cast(_validate_pdf_buildColumns, _validate_pdf_build_function.c)
_validate_pdf_build_statement = select(
    _validate_pdf_build_columns.build_id,
    _validate_pdf_build_columns.frozen_digest,
    _validate_pdf_build_columns.logical_digest,
    _validate_pdf_build_columns.contract_digest,
    _validate_pdf_build_columns.native_callbacks,
    _validate_pdf_build_columns.native_contract_digest,
)


def _validate_pdf_build_result(row: tuple[str, str, str, str, bool, str]) -> PdfBuildValidation:
    with native_result_scope("validate_pdf_build", "PdfBuildValidation"):
        return PdfBuildValidation(
            build_id=row[0],
            frozen_digest=row[1],
            logical_digest=row[2],
            contract_digest=row[3],
            native_callbacks=row[4],
            native_contract_digest=row[5],
        )


def prepare_validate_pdf_build(
    *,
    build_id: str,
    task_id: TaskId,
    attempt: TaskAttempt,
    holder: str,
    frozen_digest: str,
    projection_context: PreparedRelease | None = None,
) -> Select[str, str, str, str, bool, str]:
    _request = _validate_pdf_buildRequest(
        build_id=build_id,
        task_id=task_id,
        attempt=attempt,
        holder=holder,
        frozen_digest=frozen_digest,
    )
    if projection_context is not None:
        require_call_context(
            projection_context,
            "validate_pdf_build",
            "validate_pdf_build",
            VALIDATE_PDF_BUILD_CONTRACT_DIGEST,
        )
    return _validate_pdf_build_statement.params(
        **{
            "build_id": _request.build_id,
            "task_id": _request.task_id,
            "attempt": _request.attempt,
            "holder": _request.holder,
            "frozen_digest": _request.frozen_digest,
        }
    )


materialize_validate_pdf_build = _validate_pdf_build_result


def validate_pdf_build(
    conn: Connection,
    *,
    build_id: str,
    task_id: TaskId,
    attempt: TaskAttempt,
    holder: str,
    frozen_digest: str,
    projection_context: PreparedRelease | None = None,
) -> PdfBuildValidation:
    _statement = prepare_validate_pdf_build(
        build_id=build_id,
        task_id=task_id,
        attempt=attempt,
        holder=holder,
        frozen_digest=frozen_digest,
        projection_context=projection_context,
    )
    _native_result = conn.execute(_statement)
    with native_result_scope("validate_pdf_build", "PdfBuildValidation"):
        return _validate_pdf_build_result(_native_result.one())


READ_PDF_FROZEN_ROWS_CONTRACT_DIGEST = (
    "706d46d6a654c85e5d5e6da6b80b5ea0ff739be3d8e6bc12456f8981c1d14dff"
)


class _read_pdf_frozen_rowsRequest(OperationResult):
    build_id: str
    task_id: Annotated[
        TaskId, Field(ge=TaskId(-9223372036854775808), le=TaskId(9223372036854775807))
    ]
    attempt: Annotated[
        TaskAttempt,
        Field(ge=TaskAttempt(-9223372036854775808), le=TaskAttempt(9223372036854775807)),
    ]
    holder: str
    frozen_digest: str
    family: str
    after: JsonValue | None
    limit: Annotated[int, Field(ge=-2147483648, le=2147483647)]
    filters: JsonValue


_read_pdf_frozen_rows_function = func.ops.read_pdf_frozen_rows(
    bindparam("build_id", type_=Text()),
    bindparam("task_id", type_=BigInteger()),
    bindparam("attempt", type_=BigInteger()),
    bindparam("holder", type_=Text()),
    bindparam("frozen_digest", type_=Text()),
    bindparam("family", type_=Text()),
    bindparam("after", type_=JSONB(none_as_null=True)),
    bindparam("limit", type_=Integer()),
    bindparam("filters", type_=JSONB()),
    type_=JSONB(),
)
_read_pdf_frozen_rows_statement = select(_read_pdf_frozen_rows_function.cast(Text()))


def prepare_read_pdf_frozen_rows(
    *,
    build_id: str,
    task_id: TaskId,
    attempt: TaskAttempt,
    holder: str,
    frozen_digest: str,
    family: str,
    after: JsonValue | None,
    limit: int,
    filters: JsonValue,
    projection_context: PreparedRelease | None = None,
) -> Select[str]:
    _request = _read_pdf_frozen_rowsRequest(
        build_id=build_id,
        task_id=task_id,
        attempt=attempt,
        holder=holder,
        frozen_digest=frozen_digest,
        family=family,
        after=after,
        limit=limit,
        filters=filters,
    )
    if projection_context is not None:
        require_call_context(
            projection_context,
            "validate_pdf_build",
            "read_pdf_frozen_rows",
            READ_PDF_FROZEN_ROWS_CONTRACT_DIGEST,
        )
    return _read_pdf_frozen_rows_statement.params(
        **{
            "build_id": _request.build_id,
            "task_id": _request.task_id,
            "attempt": _request.attempt,
            "holder": _request.holder,
            "frozen_digest": _request.frozen_digest,
            "family": _request.family,
            "after": _request.after,
            "limit": _request.limit,
            "filters": _request.filters,
        }
    )


_read_pdf_frozen_rows_adapter = TypeAdapter(str)


def materialize_read_pdf_frozen_rows(row: tuple[str]) -> str:
    with native_result_scope("validate_pdf_build", "read_pdf_frozen_rows", "body"):
        checked = _read_pdf_frozen_rows_adapter.validate_python(row[0], strict=True)
        return checked


def read_pdf_frozen_rows(
    conn: Connection,
    *,
    build_id: str,
    task_id: TaskId,
    attempt: TaskAttempt,
    holder: str,
    frozen_digest: str,
    family: str,
    after: JsonValue | None,
    limit: int,
    filters: JsonValue,
    projection_context: PreparedRelease | None = None,
) -> tuple[str, ...]:
    _statement = prepare_read_pdf_frozen_rows(
        build_id=build_id,
        task_id=task_id,
        attempt=attempt,
        holder=holder,
        frozen_digest=frozen_digest,
        family=family,
        after=after,
        limit=limit,
        filters=filters,
        projection_context=projection_context,
    )
    _native_result = conn.execute(_statement)
    with native_result_scope("validate_pdf_build", "read_pdf_frozen_rows"):
        return tuple(materialize_read_pdf_frozen_rows(row) for row in _native_result)


SEAL_PDF_BUILD_CONTRACT_DIGEST = "53e9a5363ad8a7a486ec6684c3d162d9bd6897d0a14c08ee986a45660e5f7093"


class _seal_pdf_buildRequest(OperationResult):
    build_id: str
    task_id: Annotated[
        TaskId, Field(ge=TaskId(-9223372036854775808), le=TaskId(9223372036854775807))
    ]
    attempt: Annotated[
        TaskAttempt,
        Field(ge=TaskAttempt(-9223372036854775808), le=TaskAttempt(9223372036854775807)),
    ]
    holder: str
    frozen_digest: str
    product_key: str


_seal_pdf_build_function = func.ops.seal_pdf_build(
    bindparam("build_id", type_=Text()),
    bindparam("task_id", type_=BigInteger()),
    bindparam("attempt", type_=BigInteger()),
    bindparam("holder", type_=Text()),
    bindparam("frozen_digest", type_=Text()),
    bindparam("product_key", type_=Text()),
).table_valued(
    column("build_id", Text()),
    column("task_id", BigInteger()),
    column("product_key", Text()),
    column("logical_digest", Text()),
    column("release_id", Text()),
    column("source_digest", Text()),
    column("schema_digest", Text()),
    column("recipe_digest", Text()),
    column("frozen_digest", Text()),
    column("kind", Text()),
)


class _seal_pdf_buildColumns(Protocol):
    build_id: Column[str]
    task_id: Column[int]
    product_key: Column[str]
    logical_digest: Column[str]
    release_id: Column[str]
    source_digest: Column[str]
    schema_digest: Column[str]
    recipe_digest: Column[str]
    frozen_digest: Column[str]
    kind: Column[str]


_seal_pdf_build_columns = cast(_seal_pdf_buildColumns, _seal_pdf_build_function.c)
_seal_pdf_build_statement = select(
    _seal_pdf_build_columns.build_id,
    _seal_pdf_build_columns.task_id,
    _seal_pdf_build_columns.product_key,
    _seal_pdf_build_columns.logical_digest,
    _seal_pdf_build_columns.release_id,
    _seal_pdf_build_columns.source_digest,
    _seal_pdf_build_columns.schema_digest,
    _seal_pdf_build_columns.recipe_digest,
    _seal_pdf_build_columns.frozen_digest,
    _seal_pdf_build_columns.kind,
)


def _seal_pdf_build_result(
    row: tuple[str, int, str, str, str, str, str, str, str, str],
) -> PdfPublishedRevision:
    with native_result_scope("seal_pdf_build", "PdfPublishedRevision"):
        return PdfPublishedRevision(
            build_id=row[0],
            task_id=row[1],
            product_key=row[2],
            logical_digest=row[3],
            release_id=row[4],
            source_digest=row[5],
            schema_digest=row[6],
            recipe_digest=row[7],
            frozen_digest=row[8],
            kind=cast(Literal["integrated", "native"], row[9]),
        )


def prepare_seal_pdf_build(
    *,
    build_id: str,
    task_id: TaskId,
    attempt: TaskAttempt,
    holder: str,
    frozen_digest: str,
    product_key: str,
    projection_context: PreparedRelease | None = None,
) -> Select[str, int, str, str, str, str, str, str, str, str]:
    _request = _seal_pdf_buildRequest(
        build_id=build_id,
        task_id=task_id,
        attempt=attempt,
        holder=holder,
        frozen_digest=frozen_digest,
        product_key=product_key,
    )
    if projection_context is not None:
        require_call_context(
            projection_context, "seal_pdf_build", "seal_pdf_build", SEAL_PDF_BUILD_CONTRACT_DIGEST
        )
    return _seal_pdf_build_statement.params(
        **{
            "build_id": _request.build_id,
            "task_id": _request.task_id,
            "attempt": _request.attempt,
            "holder": _request.holder,
            "frozen_digest": _request.frozen_digest,
            "product_key": _request.product_key,
        }
    )


materialize_seal_pdf_build = _seal_pdf_build_result


def seal_pdf_build(
    conn: Connection,
    *,
    build_id: str,
    task_id: TaskId,
    attempt: TaskAttempt,
    holder: str,
    frozen_digest: str,
    product_key: str,
    projection_context: PreparedRelease | None = None,
) -> PdfPublishedRevision:
    _statement = prepare_seal_pdf_build(
        build_id=build_id,
        task_id=task_id,
        attempt=attempt,
        holder=holder,
        frozen_digest=frozen_digest,
        product_key=product_key,
        projection_context=projection_context,
    )
    _native_result = conn.execute(_statement)
    with native_result_scope("seal_pdf_build", "PdfPublishedRevision"):
        return _seal_pdf_build_result(_native_result.one())


LOOKUP_PDF_BUILD_CONTRACT_DIGEST = (
    "6e6388109a64905f9fb14b3274e0c3b54472f877c02511796bd5bd197b793c75"
)


class PdfStageBuild(NativeRowResult):
    build_id: str
    task_id: int
    run_id: int
    release_id: str
    source_digest: str
    recipe_digest: str
    schema_digest: str
    replay_key: str
    attempt: int
    holder: str
    state: Literal["abandoned", "frozen", "open", "published"]


class _lookup_pdf_buildRequest(OperationResult):
    task_id: Annotated[
        TaskId, Field(ge=TaskId(-9223372036854775808), le=TaskId(9223372036854775807))
    ]
    attempt: Annotated[
        TaskAttempt,
        Field(ge=TaskAttempt(-9223372036854775808), le=TaskAttempt(9223372036854775807)),
    ]
    holder: str
    replay_key: str


_lookup_pdf_build_function = func.ops.lookup_pdf_build(
    bindparam("task_id", type_=BigInteger()),
    bindparam("attempt", type_=BigInteger()),
    bindparam("holder", type_=Text()),
    bindparam("replay_key", type_=Text()),
).table_valued(
    column("build_id", Text()),
    column("task_id", BigInteger()),
    column("run_id", BigInteger()),
    column("release_id", Text()),
    column("source_digest", Text()),
    column("recipe_digest", Text()),
    column("schema_digest", Text()),
    column("replay_key", Text()),
    column("attempt", BigInteger()),
    column("holder", Text()),
    column("state", Text()),
)


class _lookup_pdf_buildColumns(Protocol):
    build_id: Column[str]
    task_id: Column[int]
    run_id: Column[int]
    release_id: Column[str]
    source_digest: Column[str]
    recipe_digest: Column[str]
    schema_digest: Column[str]
    replay_key: Column[str]
    attempt: Column[int]
    holder: Column[str]
    state: Column[str]


_lookup_pdf_build_columns = cast(_lookup_pdf_buildColumns, _lookup_pdf_build_function.c)
_lookup_pdf_build_statement = select(
    _lookup_pdf_build_columns.build_id,
    _lookup_pdf_build_columns.task_id,
    _lookup_pdf_build_columns.run_id,
    _lookup_pdf_build_columns.release_id,
    _lookup_pdf_build_columns.source_digest,
    _lookup_pdf_build_columns.recipe_digest,
    _lookup_pdf_build_columns.schema_digest,
    _lookup_pdf_build_columns.replay_key,
    _lookup_pdf_build_columns.attempt,
    _lookup_pdf_build_columns.holder,
    _lookup_pdf_build_columns.state,
)


def _lookup_pdf_build_result(
    row: tuple[str, int, int, str, str, str, str, str, int, str, str],
) -> PdfStageBuild:
    with native_result_scope("inspect_pdf_build", "PdfStageBuild"):
        return PdfStageBuild(
            build_id=row[0],
            task_id=row[1],
            run_id=row[2],
            release_id=row[3],
            source_digest=row[4],
            recipe_digest=row[5],
            schema_digest=row[6],
            replay_key=row[7],
            attempt=row[8],
            holder=row[9],
            state=cast(Literal["abandoned", "frozen", "open", "published"], row[10]),
        )


def prepare_lookup_pdf_build(
    *,
    task_id: TaskId,
    attempt: TaskAttempt,
    holder: str,
    replay_key: str,
    projection_context: PreparedRelease | None = None,
) -> Select[str, int, int, str, str, str, str, str, int, str, str]:
    _request = _lookup_pdf_buildRequest(
        task_id=task_id,
        attempt=attempt,
        holder=holder,
        replay_key=replay_key,
    )
    if projection_context is not None:
        require_call_context(
            projection_context,
            "inspect_pdf_build",
            "lookup_pdf_build",
            LOOKUP_PDF_BUILD_CONTRACT_DIGEST,
        )
    return _lookup_pdf_build_statement.params(
        **{
            "task_id": _request.task_id,
            "attempt": _request.attempt,
            "holder": _request.holder,
            "replay_key": _request.replay_key,
        }
    )


materialize_lookup_pdf_build = _lookup_pdf_build_result


def lookup_pdf_build(
    conn: Connection,
    *,
    task_id: TaskId,
    attempt: TaskAttempt,
    holder: str,
    replay_key: str,
    projection_context: PreparedRelease | None = None,
) -> PdfStageBuild | None:
    _statement = prepare_lookup_pdf_build(
        task_id=task_id,
        attempt=attempt,
        holder=holder,
        replay_key=replay_key,
        projection_context=projection_context,
    )
    _native_result = conn.execute(_statement)
    with native_result_scope("inspect_pdf_build", "PdfStageBuild"):
        row = _native_result.one_or_none()
        return None if row is None else _lookup_pdf_build_result(row)


LOOKUP_PDF_FROZEN_DIGEST_CONTRACT_DIGEST = (
    "ced53f22fd9089bd31fa92cf1e6d1a21fd68a28a133e9443d13387b0dc620524"
)


class _lookup_pdf_frozen_digestRequest(OperationResult):
    build_id: str
    task_id: Annotated[
        TaskId, Field(ge=TaskId(-9223372036854775808), le=TaskId(9223372036854775807))
    ]
    attempt: Annotated[
        TaskAttempt,
        Field(ge=TaskAttempt(-9223372036854775808), le=TaskAttempt(9223372036854775807)),
    ]
    holder: str


_lookup_pdf_frozen_digest_function = func.ops.lookup_pdf_frozen_digest(
    bindparam("build_id", type_=Text()),
    bindparam("task_id", type_=BigInteger()),
    bindparam("attempt", type_=BigInteger()),
    bindparam("holder", type_=Text()),
    type_=Text(),
)
_lookup_pdf_frozen_digest_statement = select(_lookup_pdf_frozen_digest_function)


def prepare_lookup_pdf_frozen_digest(
    *,
    build_id: str,
    task_id: TaskId,
    attempt: TaskAttempt,
    holder: str,
    projection_context: PreparedRelease | None = None,
) -> Select[str]:
    _request = _lookup_pdf_frozen_digestRequest(
        build_id=build_id,
        task_id=task_id,
        attempt=attempt,
        holder=holder,
    )
    if projection_context is not None:
        require_call_context(
            projection_context,
            "inspect_pdf_build",
            "lookup_pdf_frozen_digest",
            LOOKUP_PDF_FROZEN_DIGEST_CONTRACT_DIGEST,
        )
    return _lookup_pdf_frozen_digest_statement.params(
        **{
            "build_id": _request.build_id,
            "task_id": _request.task_id,
            "attempt": _request.attempt,
            "holder": _request.holder,
        }
    )


_lookup_pdf_frozen_digest_adapter = TypeAdapter(str)


def materialize_lookup_pdf_frozen_digest(row: tuple[str | None]) -> str | None:
    with native_result_scope("inspect_pdf_build", "lookup_pdf_frozen_digest", "frozen_digest"):
        if row[0] is None:
            return None
        checked = _lookup_pdf_frozen_digest_adapter.validate_python(row[0], strict=True)
        return checked


def lookup_pdf_frozen_digest(
    conn: Connection,
    *,
    build_id: str,
    task_id: TaskId,
    attempt: TaskAttempt,
    holder: str,
    projection_context: PreparedRelease | None = None,
) -> str | None:
    _statement = prepare_lookup_pdf_frozen_digest(
        build_id=build_id,
        task_id=task_id,
        attempt=attempt,
        holder=holder,
        projection_context=projection_context,
    )
    _native_result = conn.execute(_statement)
    with native_result_scope("inspect_pdf_build", "lookup_pdf_frozen_digest"):
        row = _native_result.one_or_none()
        if row is None:
            return None
        return materialize_lookup_pdf_frozen_digest(row)


LOOKUP_PDF_FROZEN_KIND_CONTRACT_DIGEST = (
    "372185cb34302d80300b1ffefb832e3e4fb8ca1677349630343e0e5e7ebf59de"
)


class _lookup_pdf_frozen_kindRequest(OperationResult):
    build_id: str
    task_id: Annotated[
        TaskId, Field(ge=TaskId(-9223372036854775808), le=TaskId(9223372036854775807))
    ]
    attempt: Annotated[
        TaskAttempt,
        Field(ge=TaskAttempt(-9223372036854775808), le=TaskAttempt(9223372036854775807)),
    ]
    holder: str


_lookup_pdf_frozen_kind_function = func.ops.lookup_pdf_frozen_kind(
    bindparam("build_id", type_=Text()),
    bindparam("task_id", type_=BigInteger()),
    bindparam("attempt", type_=BigInteger()),
    bindparam("holder", type_=Text()),
    type_=Text(),
)
_lookup_pdf_frozen_kind_statement = select(_lookup_pdf_frozen_kind_function)


def prepare_lookup_pdf_frozen_kind(
    *,
    build_id: str,
    task_id: TaskId,
    attempt: TaskAttempt,
    holder: str,
    projection_context: PreparedRelease | None = None,
) -> Select[str]:
    _request = _lookup_pdf_frozen_kindRequest(
        build_id=build_id,
        task_id=task_id,
        attempt=attempt,
        holder=holder,
    )
    if projection_context is not None:
        require_call_context(
            projection_context,
            "inspect_pdf_build",
            "lookup_pdf_frozen_kind",
            LOOKUP_PDF_FROZEN_KIND_CONTRACT_DIGEST,
        )
    return _lookup_pdf_frozen_kind_statement.params(
        **{
            "build_id": _request.build_id,
            "task_id": _request.task_id,
            "attempt": _request.attempt,
            "holder": _request.holder,
        }
    )


_lookup_pdf_frozen_kind_adapter = TypeAdapter(PdfFrozenBuildKind)


def materialize_lookup_pdf_frozen_kind(row: tuple[str | None]) -> PdfFrozenBuildKind | None:
    with native_result_scope("inspect_pdf_build", "lookup_pdf_frozen_kind", "kind"):
        if row[0] is None:
            return None
        checked = _lookup_pdf_frozen_kind_adapter.validate_python(row[0], strict=True)
        return checked


def lookup_pdf_frozen_kind(
    conn: Connection,
    *,
    build_id: str,
    task_id: TaskId,
    attempt: TaskAttempt,
    holder: str,
    projection_context: PreparedRelease | None = None,
) -> PdfFrozenBuildKind | None:
    _statement = prepare_lookup_pdf_frozen_kind(
        build_id=build_id,
        task_id=task_id,
        attempt=attempt,
        holder=holder,
        projection_context=projection_context,
    )
    _native_result = conn.execute(_statement)
    with native_result_scope("inspect_pdf_build", "lookup_pdf_frozen_kind"):
        row = _native_result.one_or_none()
        if row is None:
            return None
        return materialize_lookup_pdf_frozen_kind(row)


LOOKUP_PDF_PUBLISHED_BUILD_CONTRACT_DIGEST = (
    "4f7afefa6996354b819cbfe523ede5b46b85b6eaaa79fab548dc7997f3cbacbf"
)


class _lookup_pdf_published_buildRequest(OperationResult):
    build_id: str
    task_id: Annotated[
        TaskId, Field(ge=TaskId(-9223372036854775808), le=TaskId(9223372036854775807))
    ]
    attempt: Annotated[
        TaskAttempt,
        Field(ge=TaskAttempt(-9223372036854775808), le=TaskAttempt(9223372036854775807)),
    ]
    holder: str


_lookup_pdf_published_build_function = func.ops.lookup_pdf_published_build(
    bindparam("build_id", type_=Text()),
    bindparam("task_id", type_=BigInteger()),
    bindparam("attempt", type_=BigInteger()),
    bindparam("holder", type_=Text()),
).table_valued(
    column("build_id", Text()),
    column("task_id", BigInteger()),
    column("product_key", Text()),
    column("logical_digest", Text()),
    column("release_id", Text()),
    column("source_digest", Text()),
    column("schema_digest", Text()),
    column("recipe_digest", Text()),
    column("frozen_digest", Text()),
    column("kind", Text()),
)


class _lookup_pdf_published_buildColumns(Protocol):
    build_id: Column[str]
    task_id: Column[int]
    product_key: Column[str]
    logical_digest: Column[str]
    release_id: Column[str]
    source_digest: Column[str]
    schema_digest: Column[str]
    recipe_digest: Column[str]
    frozen_digest: Column[str]
    kind: Column[str]


_lookup_pdf_published_build_columns = cast(
    _lookup_pdf_published_buildColumns, _lookup_pdf_published_build_function.c
)
_lookup_pdf_published_build_statement = select(
    _lookup_pdf_published_build_columns.build_id,
    _lookup_pdf_published_build_columns.task_id,
    _lookup_pdf_published_build_columns.product_key,
    _lookup_pdf_published_build_columns.logical_digest,
    _lookup_pdf_published_build_columns.release_id,
    _lookup_pdf_published_build_columns.source_digest,
    _lookup_pdf_published_build_columns.schema_digest,
    _lookup_pdf_published_build_columns.recipe_digest,
    _lookup_pdf_published_build_columns.frozen_digest,
    _lookup_pdf_published_build_columns.kind,
)


def _lookup_pdf_published_build_result(
    row: tuple[str, int, str, str, str, str, str, str, str, str],
) -> PdfPublishedRevision:
    with native_result_scope("inspect_pdf_build", "PdfPublishedRevision"):
        return PdfPublishedRevision(
            build_id=row[0],
            task_id=row[1],
            product_key=row[2],
            logical_digest=row[3],
            release_id=row[4],
            source_digest=row[5],
            schema_digest=row[6],
            recipe_digest=row[7],
            frozen_digest=row[8],
            kind=cast(Literal["integrated", "native"], row[9]),
        )


def prepare_lookup_pdf_published_build(
    *,
    build_id: str,
    task_id: TaskId,
    attempt: TaskAttempt,
    holder: str,
    projection_context: PreparedRelease | None = None,
) -> Select[str, int, str, str, str, str, str, str, str, str]:
    _request = _lookup_pdf_published_buildRequest(
        build_id=build_id,
        task_id=task_id,
        attempt=attempt,
        holder=holder,
    )
    if projection_context is not None:
        require_call_context(
            projection_context,
            "inspect_pdf_build",
            "lookup_pdf_published_build",
            LOOKUP_PDF_PUBLISHED_BUILD_CONTRACT_DIGEST,
        )
    return _lookup_pdf_published_build_statement.params(
        **{
            "build_id": _request.build_id,
            "task_id": _request.task_id,
            "attempt": _request.attempt,
            "holder": _request.holder,
        }
    )


materialize_lookup_pdf_published_build = _lookup_pdf_published_build_result


def lookup_pdf_published_build(
    conn: Connection,
    *,
    build_id: str,
    task_id: TaskId,
    attempt: TaskAttempt,
    holder: str,
    projection_context: PreparedRelease | None = None,
) -> PdfPublishedRevision:
    _statement = prepare_lookup_pdf_published_build(
        build_id=build_id,
        task_id=task_id,
        attempt=attempt,
        holder=holder,
        projection_context=projection_context,
    )
    _native_result = conn.execute(_statement)
    with native_result_scope("inspect_pdf_build", "PdfPublishedRevision"):
        return _lookup_pdf_published_build_result(_native_result.one())


BIND_PDF_STAGE_RECIPE_CONTRACT_DIGEST = (
    "38b2f4c3318d6386c679f4a3e0a2e780c3245a58903a05f29bd3fdcf98a70a06"
)


class _bind_pdf_stage_recipeRequest(OperationResult):
    task_id: Annotated[
        TaskId, Field(ge=TaskId(-9223372036854775808), le=TaskId(9223372036854775807))
    ]
    attempt: Annotated[
        TaskAttempt,
        Field(ge=TaskAttempt(-9223372036854775808), le=TaskAttempt(9223372036854775807)),
    ]
    holder: str
    recipe: bytes


_bind_pdf_stage_recipe_function = func.ops.bind_pdf_stage_recipe(
    bindparam("task_id", type_=BigInteger()),
    bindparam("attempt", type_=BigInteger()),
    bindparam("holder", type_=Text()),
    bindparam("recipe", type_=BYTEA()),
    type_=Text(),
)
_bind_pdf_stage_recipe_statement = select(_bind_pdf_stage_recipe_function)


def prepare_bind_pdf_stage_recipe(
    *,
    task_id: TaskId,
    attempt: TaskAttempt,
    holder: str,
    recipe: bytes,
    projection_context: PreparedRelease | None = None,
) -> Select[str]:
    _request = _bind_pdf_stage_recipeRequest(
        task_id=task_id,
        attempt=attempt,
        holder=holder,
        recipe=recipe,
    )
    if projection_context is not None:
        require_call_context(
            projection_context,
            "retain_pdf_stage_recipe",
            "bind_pdf_stage_recipe",
            BIND_PDF_STAGE_RECIPE_CONTRACT_DIGEST,
        )
    return _bind_pdf_stage_recipe_statement.params(
        **{
            "task_id": _request.task_id,
            "attempt": _request.attempt,
            "holder": _request.holder,
            "recipe": _request.recipe,
        }
    )


_bind_pdf_stage_recipe_adapter = TypeAdapter(str)


def materialize_bind_pdf_stage_recipe(row: tuple[str]) -> str:
    with native_result_scope("retain_pdf_stage_recipe", "bind_pdf_stage_recipe", "recipe_digest"):
        checked = _bind_pdf_stage_recipe_adapter.validate_python(row[0], strict=True)
        return checked


def bind_pdf_stage_recipe(
    conn: Connection,
    *,
    task_id: TaskId,
    attempt: TaskAttempt,
    holder: str,
    recipe: bytes,
    projection_context: PreparedRelease | None = None,
) -> str:
    _statement = prepare_bind_pdf_stage_recipe(
        task_id=task_id,
        attempt=attempt,
        holder=holder,
        recipe=recipe,
        projection_context=projection_context,
    )
    _native_result = conn.execute(_statement)
    with native_result_scope("retain_pdf_stage_recipe", "bind_pdf_stage_recipe"):
        row = _native_result.one()
        return materialize_bind_pdf_stage_recipe(row)


ADOPT_PDF_COMPANION_CONTRACT_DIGEST = (
    "53c6473aff865a8de6d01cba0ee82d9d5f536b993e13b133878618be665c1aeb"
)


class AdoptPdfCompanionParameters(OperationResult):
    build_id: str
    task_id: Annotated[
        TaskId, Field(ge=TaskId(-9223372036854775808), le=TaskId(9223372036854775807))
    ]
    attempt: Annotated[
        TaskAttempt,
        Field(ge=TaskAttempt(-9223372036854775808), le=TaskAttempt(9223372036854775807)),
    ]
    holder: str
    family: PdfRecordCompanionFamily
    local_id: str
    body: JsonValue
    replay_key: str
    ordinal: Annotated[int, Field(ge=-9223372036854775808, le=9223372036854775807)]
    fields: JsonValue


_adopt_pdf_companion_function = func.ops.adopt_pdf_companion(
    bindparam("build_id", type_=Text()),
    bindparam("task_id", type_=BigInteger()),
    bindparam("attempt", type_=BigInteger()),
    bindparam("holder", type_=Text()),
    bindparam("family", type_=Text()),
    bindparam("local_id", type_=Text()),
    bindparam("body", type_=JSONB()),
    bindparam("replay_key", type_=Text()),
    bindparam("ordinal", type_=BigInteger()),
    bindparam("fields", type_=JSONB()),
)
_adopt_pdf_companion_statement = select(_adopt_pdf_companion_function)


def prepare_adopt_pdf_companion(
    *,
    build_id: str,
    task_id: TaskId,
    attempt: TaskAttempt,
    holder: str,
    family: PdfRecordCompanionFamily,
    local_id: str,
    body: JsonValue,
    replay_key: str,
    ordinal: int,
    fields: JsonValue,
    projection_context: PreparedRelease | None = None,
) -> Select[None]:
    _request = AdoptPdfCompanionParameters(
        build_id=build_id,
        task_id=task_id,
        attempt=attempt,
        holder=holder,
        family=family,
        local_id=local_id,
        body=body,
        replay_key=replay_key,
        ordinal=ordinal,
        fields=fields,
    )
    if projection_context is not None:
        require_call_context(
            projection_context,
            "adopt_pdf_companion_batch",
            "adopt_pdf_companion",
            ADOPT_PDF_COMPANION_CONTRACT_DIGEST,
        )
    return _adopt_pdf_companion_statement.params(
        **{
            "build_id": _request.build_id,
            "task_id": _request.task_id,
            "attempt": _request.attempt,
            "holder": _request.holder,
            "family": _request.family,
            "local_id": _request.local_id,
            "body": _request.body,
            "replay_key": _request.replay_key,
            "ordinal": _request.ordinal,
            "fields": _request.fields,
        }
    )


def adopt_pdf_companion(
    conn: Connection,
    *,
    build_id: str,
    task_id: TaskId,
    attempt: TaskAttempt,
    holder: str,
    family: PdfRecordCompanionFamily,
    local_id: str,
    body: JsonValue,
    replay_key: str,
    ordinal: int,
    fields: JsonValue,
    projection_context: PreparedRelease | None = None,
) -> None:
    _statement = prepare_adopt_pdf_companion(
        build_id=build_id,
        task_id=task_id,
        attempt=attempt,
        holder=holder,
        family=family,
        local_id=local_id,
        body=body,
        replay_key=replay_key,
        ordinal=ordinal,
        fields=fields,
        projection_context=projection_context,
    )
    _native_result = conn.execute(_statement)
    with native_result_scope("adopt_pdf_companion_batch", "adopt_pdf_companion"):
        _native_result.scalar_one()
    return None


def adopt_pdf_companion_batch(
    conn: Connection,
    *,
    requests: Sequence[AdoptPdfCompanionParameters],
    projection_context: PreparedRelease | None = None,
) -> None:
    if projection_context is not None:
        require_call_context(
            projection_context,
            "adopt_pdf_companion_batch",
            "adopt_pdf_companion",
            ADOPT_PDF_COMPANION_CONTRACT_DIGEST,
        )
    if not requests:
        return
    conn.execute(
        _adopt_pdf_companion_statement,
        [
            {
                "build_id": request.build_id,
                "task_id": request.task_id,
                "attempt": request.attempt,
                "holder": request.holder,
                "family": request.family,
                "local_id": request.local_id,
                "body": request.body,
                "replay_key": request.replay_key,
                "ordinal": request.ordinal,
                "fields": request.fields,
            }
            for request in requests
        ],
    )


BEGIN_PDF_BUILD_CONTRACT_DIGEST = "07ebb9c1c4c7a6175a57b38f5d59ce5730f6556b78db50aba7c893aa6754f0da"


class _begin_pdf_buildRequest(OperationResult):
    task_id: Annotated[
        TaskId, Field(ge=TaskId(-9223372036854775808), le=TaskId(9223372036854775807))
    ]
    attempt: Annotated[
        TaskAttempt,
        Field(ge=TaskAttempt(-9223372036854775808), le=TaskAttempt(9223372036854775807)),
    ]
    holder: str
    source_digest: str
    recipe_digest: str
    schema_digest: str
    replay_key: str


_begin_pdf_build_function = func.ops.begin_pdf_build(
    bindparam("task_id", type_=BigInteger()),
    bindparam("attempt", type_=BigInteger()),
    bindparam("holder", type_=Text()),
    bindparam("source_digest", type_=Text()),
    bindparam("recipe_digest", type_=Text()),
    bindparam("schema_digest", type_=Text()),
    bindparam("replay_key", type_=Text()),
).table_valued(
    column("build_id", Text()),
    column("task_id", BigInteger()),
    column("run_id", BigInteger()),
    column("release_id", Text()),
    column("source_digest", Text()),
    column("recipe_digest", Text()),
    column("schema_digest", Text()),
    column("replay_key", Text()),
    column("attempt", BigInteger()),
    column("holder", Text()),
    column("state", Text()),
)


class _begin_pdf_buildColumns(Protocol):
    build_id: Column[str]
    task_id: Column[int]
    run_id: Column[int]
    release_id: Column[str]
    source_digest: Column[str]
    recipe_digest: Column[str]
    schema_digest: Column[str]
    replay_key: Column[str]
    attempt: Column[int]
    holder: Column[str]
    state: Column[str]


_begin_pdf_build_columns = cast(_begin_pdf_buildColumns, _begin_pdf_build_function.c)
_begin_pdf_build_statement = select(
    _begin_pdf_build_columns.build_id,
    _begin_pdf_build_columns.task_id,
    _begin_pdf_build_columns.run_id,
    _begin_pdf_build_columns.release_id,
    _begin_pdf_build_columns.source_digest,
    _begin_pdf_build_columns.recipe_digest,
    _begin_pdf_build_columns.schema_digest,
    _begin_pdf_build_columns.replay_key,
    _begin_pdf_build_columns.attempt,
    _begin_pdf_build_columns.holder,
    _begin_pdf_build_columns.state,
)


def _begin_pdf_build_result(
    row: tuple[str, int, int, str, str, str, str, str, int, str, str],
) -> PdfStageBuild:
    with native_result_scope("begin_pdf_build", "PdfStageBuild"):
        return PdfStageBuild(
            build_id=row[0],
            task_id=row[1],
            run_id=row[2],
            release_id=row[3],
            source_digest=row[4],
            recipe_digest=row[5],
            schema_digest=row[6],
            replay_key=row[7],
            attempt=row[8],
            holder=row[9],
            state=cast(Literal["abandoned", "frozen", "open", "published"], row[10]),
        )


def prepare_begin_pdf_build(
    *,
    task_id: TaskId,
    attempt: TaskAttempt,
    holder: str,
    source_digest: str,
    recipe_digest: str,
    schema_digest: str,
    replay_key: str,
    projection_context: PreparedRelease | None = None,
) -> Select[str, int, int, str, str, str, str, str, int, str, str]:
    _request = _begin_pdf_buildRequest(
        task_id=task_id,
        attempt=attempt,
        holder=holder,
        source_digest=source_digest,
        recipe_digest=recipe_digest,
        schema_digest=schema_digest,
        replay_key=replay_key,
    )
    if projection_context is not None:
        require_call_context(
            projection_context,
            "begin_pdf_build",
            "begin_pdf_build",
            BEGIN_PDF_BUILD_CONTRACT_DIGEST,
        )
    return _begin_pdf_build_statement.params(
        **{
            "task_id": _request.task_id,
            "attempt": _request.attempt,
            "holder": _request.holder,
            "source_digest": _request.source_digest,
            "recipe_digest": _request.recipe_digest,
            "schema_digest": _request.schema_digest,
            "replay_key": _request.replay_key,
        }
    )


materialize_begin_pdf_build = _begin_pdf_build_result


def begin_pdf_build(
    conn: Connection,
    *,
    task_id: TaskId,
    attempt: TaskAttempt,
    holder: str,
    source_digest: str,
    recipe_digest: str,
    schema_digest: str,
    replay_key: str,
    projection_context: PreparedRelease | None = None,
) -> PdfStageBuild:
    _statement = prepare_begin_pdf_build(
        task_id=task_id,
        attempt=attempt,
        holder=holder,
        source_digest=source_digest,
        recipe_digest=recipe_digest,
        schema_digest=schema_digest,
        replay_key=replay_key,
        projection_context=projection_context,
    )
    _native_result = conn.execute(_statement)
    with native_result_scope("begin_pdf_build", "PdfStageBuild"):
        return _begin_pdf_build_result(_native_result.one())


PREPARE_PDF_STAGE_CONTRACT_DIGEST = (
    "4a9181fd6ee426743f54e83ec63cea1a34f61dbf9cdf11802685b4f8353ba42b"
)


class _prepare_pdf_stageRequest(OperationResult):
    build_id: str
    task_id: Annotated[
        TaskId, Field(ge=TaskId(-9223372036854775808), le=TaskId(9223372036854775807))
    ]
    attempt: Annotated[
        TaskAttempt,
        Field(ge=TaskAttempt(-9223372036854775808), le=TaskAttempt(9223372036854775807)),
    ]
    holder: str


_prepare_pdf_stage_function = func.ops.prepare_pdf_stage(
    bindparam("build_id", type_=Text()),
    bindparam("task_id", type_=BigInteger()),
    bindparam("attempt", type_=BigInteger()),
    bindparam("holder", type_=Text()),
)
_prepare_pdf_stage_statement = select(_prepare_pdf_stage_function)


def prepare_prepare_pdf_stage(
    *,
    build_id: str,
    task_id: TaskId,
    attempt: TaskAttempt,
    holder: str,
    projection_context: PreparedRelease | None = None,
) -> Select[None]:
    _request = _prepare_pdf_stageRequest(
        build_id=build_id,
        task_id=task_id,
        attempt=attempt,
        holder=holder,
    )
    if projection_context is not None:
        require_call_context(
            projection_context,
            "adopt_pdf_batch",
            "prepare_pdf_stage",
            PREPARE_PDF_STAGE_CONTRACT_DIGEST,
        )
    return _prepare_pdf_stage_statement.params(
        **{
            "build_id": _request.build_id,
            "task_id": _request.task_id,
            "attempt": _request.attempt,
            "holder": _request.holder,
        }
    )


def prepare_pdf_stage(
    conn: Connection,
    *,
    build_id: str,
    task_id: TaskId,
    attempt: TaskAttempt,
    holder: str,
    projection_context: PreparedRelease | None = None,
) -> None:
    _statement = prepare_prepare_pdf_stage(
        build_id=build_id,
        task_id=task_id,
        attempt=attempt,
        holder=holder,
        projection_context=projection_context,
    )
    _native_result = conn.execute(_statement)
    with native_result_scope("adopt_pdf_batch", "prepare_pdf_stage"):
        _native_result.scalar_one()
    return None


ADOPT_PDF_BATCH_CONTRACT_DIGEST = "28fb30e3b6f5b9e4070a53698f8ced447299fd976a48794214360b8c1f9f3f52"


class PdfStageReceipt(NativeRowResult):
    build_id: str
    replay_key: str
    content_digest: str
    row_count: int


class _adopt_pdf_batchRequest(OperationResult):
    build_id: str
    task_id: Annotated[
        TaskId, Field(ge=TaskId(-9223372036854775808), le=TaskId(9223372036854775807))
    ]
    attempt: Annotated[
        TaskAttempt,
        Field(ge=TaskAttempt(-9223372036854775808), le=TaskAttempt(9223372036854775807)),
    ]
    holder: str
    replay_key: str


_adopt_pdf_batch_function = func.ops.adopt_pdf_batch(
    bindparam("build_id", type_=Text()),
    bindparam("task_id", type_=BigInteger()),
    bindparam("attempt", type_=BigInteger()),
    bindparam("holder", type_=Text()),
    bindparam("replay_key", type_=Text()),
).table_valued(
    column("build_id", Text()),
    column("replay_key", Text()),
    column("content_digest", Text()),
    column("row_count", BigInteger()),
)


class _adopt_pdf_batchColumns(Protocol):
    build_id: Column[str]
    replay_key: Column[str]
    content_digest: Column[str]
    row_count: Column[int]


_adopt_pdf_batch_columns = cast(_adopt_pdf_batchColumns, _adopt_pdf_batch_function.c)
_adopt_pdf_batch_statement = select(
    _adopt_pdf_batch_columns.build_id,
    _adopt_pdf_batch_columns.replay_key,
    _adopt_pdf_batch_columns.content_digest,
    _adopt_pdf_batch_columns.row_count,
)


def _adopt_pdf_batch_result(row: tuple[str, str, str, int]) -> PdfStageReceipt:
    with native_result_scope("adopt_pdf_batch", "PdfStageReceipt"):
        return PdfStageReceipt(
            build_id=row[0],
            replay_key=row[1],
            content_digest=row[2],
            row_count=row[3],
        )


def prepare_adopt_pdf_batch(
    *,
    build_id: str,
    task_id: TaskId,
    attempt: TaskAttempt,
    holder: str,
    replay_key: str,
    projection_context: PreparedRelease | None = None,
) -> Select[str, str, str, int]:
    _request = _adopt_pdf_batchRequest(
        build_id=build_id,
        task_id=task_id,
        attempt=attempt,
        holder=holder,
        replay_key=replay_key,
    )
    if projection_context is not None:
        require_call_context(
            projection_context,
            "adopt_pdf_batch",
            "adopt_pdf_batch",
            ADOPT_PDF_BATCH_CONTRACT_DIGEST,
        )
    return _adopt_pdf_batch_statement.params(
        **{
            "build_id": _request.build_id,
            "task_id": _request.task_id,
            "attempt": _request.attempt,
            "holder": _request.holder,
            "replay_key": _request.replay_key,
        }
    )


materialize_adopt_pdf_batch = _adopt_pdf_batch_result


def adopt_pdf_batch(
    conn: Connection,
    *,
    build_id: str,
    task_id: TaskId,
    attempt: TaskAttempt,
    holder: str,
    replay_key: str,
    projection_context: PreparedRelease | None = None,
) -> PdfStageReceipt:
    _statement = prepare_adopt_pdf_batch(
        build_id=build_id,
        task_id=task_id,
        attempt=attempt,
        holder=holder,
        replay_key=replay_key,
        projection_context=projection_context,
    )
    _native_result = conn.execute(_statement)
    with native_result_scope("adopt_pdf_batch", "PdfStageReceipt"):
        return _adopt_pdf_batch_result(_native_result.one())


INSPECT_PDF_PROGRESS_CONTRACT_DIGEST = (
    "89b897282df600cf371baeec1ce37caa380a81f678f460a5416d677ddc92a9a0"
)


class _inspect_pdf_progressRequest(OperationResult):
    build_id: str
    task_id: Annotated[
        TaskId, Field(ge=TaskId(-9223372036854775808), le=TaskId(9223372036854775807))
    ]
    attempt: Annotated[
        TaskAttempt,
        Field(ge=TaskAttempt(-9223372036854775808), le=TaskAttempt(9223372036854775807)),
    ]
    holder: str


_inspect_pdf_progress_function = func.ops.inspect_pdf_progress(
    bindparam("build_id", type_=Text()),
    bindparam("task_id", type_=BigInteger()),
    bindparam("attempt", type_=BigInteger()),
    bindparam("holder", type_=Text()),
).table_valued(
    column("build_id", Text()),
    column("replay_key", Text()),
    column("content_digest", Text()),
    column("row_count", BigInteger()),
)


class _inspect_pdf_progressColumns(Protocol):
    build_id: Column[str]
    replay_key: Column[str]
    content_digest: Column[str]
    row_count: Column[int]


_inspect_pdf_progress_columns = cast(_inspect_pdf_progressColumns, _inspect_pdf_progress_function.c)
_inspect_pdf_progress_statement = select(
    _inspect_pdf_progress_columns.build_id,
    _inspect_pdf_progress_columns.replay_key,
    _inspect_pdf_progress_columns.content_digest,
    _inspect_pdf_progress_columns.row_count,
)


def _inspect_pdf_progress_result(row: tuple[str, str, str, int]) -> PdfStageReceipt:
    with native_result_scope("inspect_pdf_progress", "PdfStageReceipt"):
        return PdfStageReceipt(
            build_id=row[0],
            replay_key=row[1],
            content_digest=row[2],
            row_count=row[3],
        )


def prepare_inspect_pdf_progress(
    *,
    build_id: str,
    task_id: TaskId,
    attempt: TaskAttempt,
    holder: str,
    projection_context: PreparedRelease | None = None,
) -> Select[str, str, str, int]:
    _request = _inspect_pdf_progressRequest(
        build_id=build_id,
        task_id=task_id,
        attempt=attempt,
        holder=holder,
    )
    if projection_context is not None:
        require_call_context(
            projection_context,
            "inspect_pdf_progress",
            "inspect_pdf_progress",
            INSPECT_PDF_PROGRESS_CONTRACT_DIGEST,
        )
    return _inspect_pdf_progress_statement.params(
        **{
            "build_id": _request.build_id,
            "task_id": _request.task_id,
            "attempt": _request.attempt,
            "holder": _request.holder,
        }
    )


materialize_inspect_pdf_progress = _inspect_pdf_progress_result


def inspect_pdf_progress(
    conn: Connection,
    *,
    build_id: str,
    task_id: TaskId,
    attempt: TaskAttempt,
    holder: str,
    projection_context: PreparedRelease | None = None,
) -> tuple[PdfStageReceipt, ...]:
    _statement = prepare_inspect_pdf_progress(
        build_id=build_id,
        task_id=task_id,
        attempt=attempt,
        holder=holder,
        projection_context=projection_context,
    )
    _native_result = conn.execute(_statement)
    with native_result_scope("inspect_pdf_progress", "PdfStageReceipt"):
        return tuple(_inspect_pdf_progress_result(row) for row in _native_result)


RESUME_PDF_BUILD_CONTRACT_DIGEST = (
    "d1d673c95f4231203b636e403810332cfb87dd2548731647903e8c3b2e9cb5e9"
)


class _resume_pdf_buildRequest(OperationResult):
    build_id: str
    task_id: Annotated[
        TaskId, Field(ge=TaskId(-9223372036854775808), le=TaskId(9223372036854775807))
    ]
    attempt: Annotated[
        TaskAttempt,
        Field(ge=TaskAttempt(-9223372036854775808), le=TaskAttempt(9223372036854775807)),
    ]
    holder: str


_resume_pdf_build_function = func.ops.resume_pdf_build(
    bindparam("build_id", type_=Text()),
    bindparam("task_id", type_=BigInteger()),
    bindparam("attempt", type_=BigInteger()),
    bindparam("holder", type_=Text()),
)
_resume_pdf_build_statement = select(_resume_pdf_build_function)


def prepare_resume_pdf_build(
    *,
    build_id: str,
    task_id: TaskId,
    attempt: TaskAttempt,
    holder: str,
    projection_context: PreparedRelease | None = None,
) -> Select[None]:
    _request = _resume_pdf_buildRequest(
        build_id=build_id,
        task_id=task_id,
        attempt=attempt,
        holder=holder,
    )
    if projection_context is not None:
        require_call_context(
            projection_context,
            "resume_pdf_build",
            "resume_pdf_build",
            RESUME_PDF_BUILD_CONTRACT_DIGEST,
        )
    return _resume_pdf_build_statement.params(
        **{
            "build_id": _request.build_id,
            "task_id": _request.task_id,
            "attempt": _request.attempt,
            "holder": _request.holder,
        }
    )


def resume_pdf_build(
    conn: Connection,
    *,
    build_id: str,
    task_id: TaskId,
    attempt: TaskAttempt,
    holder: str,
    projection_context: PreparedRelease | None = None,
) -> None:
    _statement = prepare_resume_pdf_build(
        build_id=build_id,
        task_id=task_id,
        attempt=attempt,
        holder=holder,
        projection_context=projection_context,
    )
    _native_result = conn.execute(_statement)
    with native_result_scope("resume_pdf_build", "resume_pdf_build"):
        _native_result.scalar_one()
    return None


ABANDON_PDF_BUILD_CONTRACT_DIGEST = (
    "6e721535367083e0f8950f4105ee71bdf5bb40cda94545ee558d2a1739d85f8a"
)


class _abandon_pdf_buildRequest(OperationResult):
    build_id: str
    task_id: Annotated[
        TaskId, Field(ge=TaskId(-9223372036854775808), le=TaskId(9223372036854775807))
    ]
    attempt: Annotated[
        TaskAttempt,
        Field(ge=TaskAttempt(-9223372036854775808), le=TaskAttempt(9223372036854775807)),
    ]
    holder: str


_abandon_pdf_build_function = func.ops.abandon_pdf_build(
    bindparam("build_id", type_=Text()),
    bindparam("task_id", type_=BigInteger()),
    bindparam("attempt", type_=BigInteger()),
    bindparam("holder", type_=Text()),
)
_abandon_pdf_build_statement = select(_abandon_pdf_build_function)


def prepare_abandon_pdf_build(
    *,
    build_id: str,
    task_id: TaskId,
    attempt: TaskAttempt,
    holder: str,
    projection_context: PreparedRelease | None = None,
) -> Select[None]:
    _request = _abandon_pdf_buildRequest(
        build_id=build_id,
        task_id=task_id,
        attempt=attempt,
        holder=holder,
    )
    if projection_context is not None:
        require_call_context(
            projection_context,
            "abandon_pdf_build",
            "abandon_pdf_build",
            ABANDON_PDF_BUILD_CONTRACT_DIGEST,
        )
    return _abandon_pdf_build_statement.params(
        **{
            "build_id": _request.build_id,
            "task_id": _request.task_id,
            "attempt": _request.attempt,
            "holder": _request.holder,
        }
    )


def abandon_pdf_build(
    conn: Connection,
    *,
    build_id: str,
    task_id: TaskId,
    attempt: TaskAttempt,
    holder: str,
    projection_context: PreparedRelease | None = None,
) -> None:
    _statement = prepare_abandon_pdf_build(
        build_id=build_id,
        task_id=task_id,
        attempt=attempt,
        holder=holder,
        projection_context=projection_context,
    )
    _native_result = conn.execute(_statement)
    with native_result_scope("abandon_pdf_build", "abandon_pdf_build"):
        _native_result.scalar_one()
    return None


RECORD_DIRECTION_CONTRACT_DIGEST = (
    "86f5b0cb523ff885a1ec30246f326ec0bedc34cb45d45023371a9dfc2becff59"
)


class _record_directionRequest(OperationResult):
    run_id: Annotated[RunId, Field(ge=RunId(-9223372036854775808), le=RunId(9223372036854775807))]
    actor: str
    session_ref: str
    body: JsonValue


_record_direction_function = func.ops.record_direction(
    bindparam("run_id", type_=BigInteger()),
    bindparam("actor", type_=Text()),
    bindparam("session_ref", type_=Text()),
    bindparam("body", type_=JSONB()),
    type_=BigInteger(),
)
_record_direction_statement = select(_record_direction_function)


def prepare_record_direction(
    *,
    run_id: RunId,
    actor: str,
    session_ref: str,
    body: JsonValue,
    projection_context: PreparedRelease | None = None,
) -> Select[int]:
    _request = _record_directionRequest(
        run_id=run_id,
        actor=actor,
        session_ref=session_ref,
        body=body,
    )
    if projection_context is not None:
        require_call_context(
            projection_context,
            "record_direction",
            "record_direction",
            RECORD_DIRECTION_CONTRACT_DIGEST,
        )
    return _record_direction_statement.params(
        **{
            "run_id": _request.run_id,
            "actor": _request.actor,
            "session_ref": _request.session_ref,
            "body": _request.body,
        }
    )


_record_direction_adapter = TypeAdapter(InterventionId)


def materialize_record_direction(row: tuple[int]) -> InterventionId:
    with native_result_scope("record_direction", "record_direction", "intervention_id"):
        checked = _record_direction_adapter.validate_python(row[0], strict=True)
        return checked


def record_direction(
    conn: Connection,
    *,
    run_id: RunId,
    actor: str,
    session_ref: str,
    body: JsonValue,
    projection_context: PreparedRelease | None = None,
) -> InterventionId:
    _statement = prepare_record_direction(
        run_id=run_id,
        actor=actor,
        session_ref=session_ref,
        body=body,
        projection_context=projection_context,
    )
    _native_result = conn.execute(_statement)
    with native_result_scope("record_direction", "record_direction"):
        row = _native_result.one()
        return materialize_record_direction(row)


CALL_CONTRACT_DIGEST = "a804aba699e279e9f133e480351002cecf297673e27d740fa50f4869a056dea4"
