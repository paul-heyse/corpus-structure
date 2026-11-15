"""Generated from execution call correspondences; do not edit."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import (
    Annotated,
    Protocol,
    TypedDict,
    cast,
)

from pydantic import Field, JsonValue, TypeAdapter
from sqlalchemy import (
    BigInteger,
    Boolean,
    Column,
    Connection,
    DateTime,
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

from corpus_structure.core.vocab import TaskUnitType

from ._operation_ids import CompletionReceiptProtocol as CompletionReceiptProtocol
from ._operation_ids import CompletionResultTransaction as CompletionResultTransaction
from ._operation_ids import CutId as CutId
from ._operation_ids import DocumentId as DocumentId
from ._operation_ids import InterventionId as InterventionId
from ._operation_ids import MethodConfigId as MethodConfigId
from ._operation_ids import MethodId as MethodId
from ._operation_ids import NativeAdmissionParametersPurpose as NativeAdmissionParametersPurpose
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
)
from .operation_value_types import require_call_context as require_call_context
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
    protocol: CompletionReceiptProtocol
    observation_ids: tuple[int, ...]
    result_digest: str


PREPARE_RELEASE_ARCHIVE_CONTRACT_DIGEST = (
    "287905734a4062e84f2d08ecafa0e03c527ec66aba14b6cd049b2cf9789a17d3"
)


class _prepare_release_archiveRequest(OperationResult):
    release_id: ReleaseId


_prepare_release_archive_function = func.sem.prepare_release_archive(
    bindparam("release_id", type_=Text()),
)
_prepare_release_archive_statement = select(_prepare_release_archive_function)


def prepare_prepare_release_archive(
    *,
    release_id: ReleaseId,
    projection_context: PreparedRelease | None = None,
) -> Select[None]:
    _request = _prepare_release_archiveRequest(
        release_id=release_id,
    )
    if projection_context is not None:
        require_call_context(
            projection_context,
            "archive",
            "prepare_release_archive",
            PREPARE_RELEASE_ARCHIVE_CONTRACT_DIGEST,
        )
    return _prepare_release_archive_statement.params(
        **{
            "release_id": _request.release_id,
        }
    )


def prepare_release_archive(
    conn: Connection,
    *,
    release_id: ReleaseId,
    projection_context: PreparedRelease | None = None,
) -> None:
    _statement = prepare_prepare_release_archive(
        release_id=release_id,
        projection_context=projection_context,
    )
    _native_result = conn.execute(_statement)
    with native_result_scope("archive", "prepare_release_archive"):
        _native_result.scalar_one()
    return None


PUBLISH_RELEASE_ARCHIVE_CONTRACT_DIGEST = (
    "7a7e485a62254bd81b62866ce3bab029a50e2b5a6ab528bd002a4461eebb3e45"
)


class _publish_release_archiveRequest(OperationResult):
    release_id: ReleaseId


_publish_release_archive_function = func.sem.publish_release_archive(
    bindparam("release_id", type_=Text()),
    type_=Text(),
)
_publish_release_archive_statement = select(_publish_release_archive_function)


def prepare_publish_release_archive(
    *,
    release_id: ReleaseId,
    projection_context: PreparedRelease | None = None,
) -> Select[str]:
    _request = _publish_release_archiveRequest(
        release_id=release_id,
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
            "release_id": _request.release_id,
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
    release_id: ReleaseId,
    projection_context: PreparedRelease | None = None,
) -> ReleaseId:
    _statement = prepare_publish_release_archive(
        release_id=release_id,
        projection_context=projection_context,
    )
    _native_result = conn.execute(_statement)
    with native_result_scope("archive", "publish_release_archive"):
        row = _native_result.one()
        return materialize_publish_release_archive(row)


ACTIVATE_RELEASE_CONTRACT_DIGEST = (
    "4c0fd1f82bbd121cf72080b39b2c8feaee06cd6700c70b76f4d27b2ee57e9105"
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


REGISTER_RUNTIME_BINDING_CONTRACT_DIGEST = (
    "d3c89f02224b64ead142524a383fa2aef9721f9d8c98344ac079ef65eb5b797d"
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


CREATE_RUN_CONTRACT_DIGEST = "92b0350c481aad0fdb2f1c5c9dd950d3314a758ef5ce328a0b67e9f59dee6bff"


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


BEGIN_RUN_CONTRACT_DIGEST = "e74eff9a2ea3158315b9d75287edba5474c39965d5a23fe84507a31452d44792"


class _begin_runRequest(OperationResult):
    run_id: Annotated[RunId, Field(ge=RunId(-9223372036854775808), le=RunId(9223372036854775807))]


_begin_run_function = func.ops.begin_run(
    bindparam("run_id", type_=BigInteger()),
    type_=BigInteger(),
)
_begin_run_statement = select(_begin_run_function)


def prepare_begin_run(
    *,
    run_id: RunId,
    projection_context: PreparedRelease | None = None,
) -> Select[int]:
    _request = _begin_runRequest(
        run_id=run_id,
    )
    if projection_context is not None:
        require_call_context(
            projection_context, "start_run", "begin_run", BEGIN_RUN_CONTRACT_DIGEST
        )
    return _begin_run_statement.params(
        **{
            "run_id": _request.run_id,
        }
    )


_begin_run_adapter = TypeAdapter(RunId)


def materialize_begin_run(row: tuple[int]) -> RunId:
    with native_result_scope("start_run", "begin_run", "run_id"):
        checked = _begin_run_adapter.validate_python(row[0], strict=True)
        return checked


def begin_run(
    conn: Connection,
    *,
    run_id: RunId,
    projection_context: PreparedRelease | None = None,
) -> RunId:
    _statement = prepare_begin_run(
        run_id=run_id,
        projection_context=projection_context,
    )
    _native_result = conn.execute(_statement)
    with native_result_scope("start_run", "begin_run"):
        row = _native_result.one()
        return materialize_begin_run(row)


METHOD_DEFINITION_CONTRACT_DIGEST = (
    "54f6025359eb6612ae8fa20411087120c2c8b31f0fa79848bdb290ce3f5474df"
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
    id: Named[MethodId]
    name: Named[str]
    version: Named[str]
    unit_type: Named[str | None]
    configuration_schema_digest: Named[str | None]
    family: Named[str]
    tier: Named[str]
    confidence_source: Named[str | None]


class _method_definition_ops_methodColumnsProtocol(Protocol):
    id: Column[MethodId]
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
    ColumnElement[MethodId],
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
    result: Result[MethodId, str, str, str | None, str | None, str, str, str | None],
) -> RecordedMethod:
    with native_result_scope("configure_method", "RecordedMethod"):
        return materialize_method_definition(result.one())


METHOD_CONFIGURATION_CONTRACT_DIGEST = (
    "23c74ad4e8c15424fb2d7b18fc54582ffe11d656ccb5ec607adc4059f194d89f"
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
    id: Named[MethodConfigId]
    method_id: Named[MethodId]
    name: Named[str]
    params: Named[JsonValue]
    config_hash: Named[str]


class _method_configuration_ops_method_configColumnsProtocol(Protocol):
    id: Column[MethodConfigId]
    method_id: Column[MethodId]
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
    ColumnElement[MethodConfigId],
    ColumnElement[MethodId],
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


def collect_method_configuration(
    result: Result[MethodConfigId, MethodId, str, str, str],
) -> RecordedMethodConfig:
    with native_result_scope("configure_method", "RecordedMethodConfig"):
        return materialize_method_configuration(result.one())


LOCK_SCHEDULE_RUN_CONTRACT_DIGEST = (
    "23486766fc983fa52a9654a1b3dfaef04b3c86b634028866d3127c63f3721289"
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
    return cast(
        Select[
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
        _lock_schedule_run_statement.params(
            **{
                "run_id": _request.run_id,
                "operation": _request.operation,
            }
        ),
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


CLAIM_TASKS_CONTRACT_DIGEST = "b367694d447555e93faab7057163d260ab8a6e7ed17d3603c69db71945393981"


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
    id: Column[TaskId]
    run_id: Column[RunId | None]
    release_id: Column[ReleaseId]
    method_config_id: Column[MethodConfigId | None]
    unit_type: Column[str | None]
    unit_id: Column[int | None]
    unit_key: Column[str | None]
    packet_hash: Column[str | None]
    attempt: Column[TaskAttempt]
    claimed_by: Column[str | None]
    lease_until: Column[datetime | None]
    invocation_key: Column[str]
    error: Column[JsonValue | None]


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
        int | None,
        str,
        int | None,
        str | None,
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
            run_id=RunId(_required(row[1], "run_id", "ClaimedTask", "claim")),
            release_id=ReleaseId(row[2]),
            method_config_id=MethodConfigId(
                _required(row[3], "method_config_id", "ClaimedTask", "claim")
            ),
            unit_type=native_result_value(
                "claim",
                "ClaimedTask",
                "unit_type",
                TaskUnitType,
                _required(row[4], "unit_type", "ClaimedTask", "claim"),
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
    TaskId,
    RunId | None,
    ReleaseId,
    MethodConfigId | None,
    str | None,
    int | None,
    str | None,
    str | None,
    TaskAttempt,
    str | None,
    datetime | None,
    str,
    JsonValue | None,
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
    return cast(
        Select[
            TaskId,
            RunId | None,
            ReleaseId,
            MethodConfigId | None,
            str | None,
            int | None,
            str | None,
            str | None,
            TaskAttempt,
            str | None,
            datetime | None,
            str,
            JsonValue | None,
        ],
        _claim_tasks_statement.params(
            **{
                "run_id": _request.run_id,
                "config_id": _request.config_id,
                "holder": _request.holder,
                "limit": _request.limit,
                "agent": _request.agent,
            }
        ),
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


COMPLETE_TASK_CONTRACT_DIGEST = "c3ea8e3c696c1410b86166f86977cafc8c0ce5788a2920ab67ec3e5456c5c76f"


class CompletionResult(OperationResult):
    receipt: CompletionReceipt
    transaction: CompletionResultTransaction


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
    "128856c79ca808b64bc948b31f819c35d55190a1aad2bcecacd24478858f6dbd"
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
    id: Column[RunId]


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
) -> Select[RunId]:
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
    "ab79b3909d5af50873e0b85f4040cd089a2833ef9e9e12616702e2a77e33acac"
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
    "8221999ee8c22e558dcf942cc7600e32a1c9c6b76b5e9b701aa7fc071d790a74"
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


CAPTURE_CUT_CONTRACT_DIGEST = "8dd71c6d97fda8c2300fe445549a559012156d4514611b0d3d9d00897fb8e779"


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


END_SOURCE_RUN_CONTRACT_DIGEST = "e66d7a83baea00eff56c4d1e91a4bbaf5e792ed1f6ffe57f6343a1f680cd109d"


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


ORIGINAL_DESCRIPTOR_CONTRACT_DIGEST = (
    "ec7ed48c312815a2aa4810a5a256f8011b249e53302325671b9a98ae65a00627"
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
    "955040903aaf3fd6f18b5f60c005d29d0e503dbeb401a811dea8e885459e6470"
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
    "a8d181490c8eda21082704c3b647ef83735c72dc425bb5cf0c39709affff372b"
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
    "134b786dc0b8d995867a5120b894a0e17192f78c1cfc6e8f86a3f3dca122a467"
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
    "6508baeada513a9edbfef3a3cc0c16ea087fd75422680920ac85ae7b2161d625"
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
    return cast(
        Select[
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
        _lock_finalization_run_statement.params(
            **{
                "run_id": _request.run_id,
            }
        ),
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
    "f1a5d78fe55af8c34db5402ece57c59b3d87ed82991860dc0c4c0e126ee69ae5"
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
    "47423ca83741e9e5fd3ea9581eba70296987a0b1e30a912fb1eb6d73e32511ca"
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


PUBLISH_BATCH_CONTRACT_DIGEST = "59c8ce8646ba0df1f04e239010f3f94ca75100cb6a8bca4f10abc74d695093ce"


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
    "ff1c5aa7194038bcf5c6ea50640ae8d97938aa75286129ca427bc9f6e7afa0fc"
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
    "80f70a288d2e3c58a2387825a031f1832728a73a87925cf37de6cb002eb84fc4"
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
    "187959f14dccb0f2217512f8ed3db9d356df9547ee69ef88cbd8acb97efe39b6"
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
    "94b3bd508b50de36c3eb672e85c34dd2ac5206df9554225ebe588f810959450e"
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
    "50ded593633dd723c83f9207d50be3f22b3f800b76f5a1f26abbed0cc1671cf8"
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


RENEW_CLAIM_CONTRACT_DIGEST = "48ecec2a1e46cdd04c083a837cafa226c889f5145ec9ac4e512c85156c2ecdaf"


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


RELEASE_CLAIM_CONTRACT_DIGEST = "10719671de78ec6b90ec203c52d4e53cd88b15a0fb62fead69bdf83bb60175c5"


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
    "f0c22b25ba4b8d230151d74716f0029569033c16a9657c73eb46a8f61dc4c33a"
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


PUBLISH_SOURCE_VIEW_CONTRACT_DIGEST = (
    "ca34ab2b929f69c7fd722cd1f01b526e954699b9a01d6f8e3dd8cacde60f19dd"
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
    "dc144fd2662a5a91fd0137856df6493cb93a77e1c2211e92c6374481fe543ec6"
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
    "ad5207636616035360f2fd205b957c9e97e34b9e77bc68da52f1b7d4e86de27b"
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


CAPTURE_NATIVE_SOURCE_FRAME_CONTRACT_DIGEST = (
    "9cfbb73c337654b7f42397ef53eac805f3ed851233bb9b8619f864758e7837bf"
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


RECORD_DIRECTION_CONTRACT_DIGEST = (
    "8a947e69efc98970abae502736cb8bf5880a8e583a8fed1184c03fefc76b3de4"
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


OPERATION_EVALUATION_PAGE_CONTRACT_DIGEST = (
    "e46f1b6798a6f43be2438f8089dec9b9c19d1d576fff9ea3f3a4192d8cbfd1c5"
)


class _operation_evaluation_pageRequest(OperationResult):
    project_id: ProjectId
    evaluation_id: Annotated[int, Field(ge=-9223372036854775808, le=9223372036854775807)]
    view: str
    facet: str | None
    direction: str | None
    cursor: str | None
    limit: Annotated[int, Field(ge=-9223372036854775808, le=9223372036854775807)]
    max_bytes: Annotated[int, Field(ge=-9223372036854775808, le=9223372036854775807)]


_operation_evaluation_page_function = func.eval.operation_evaluation_page(
    bindparam("project_id", type_=Text()),
    bindparam("evaluation_id", type_=BigInteger()),
    bindparam("view", type_=Text()),
    bindparam("facet", type_=Text()),
    bindparam("direction", type_=Text()),
    bindparam("cursor", type_=Text()),
    bindparam("limit", type_=BigInteger()),
    bindparam("max_bytes", type_=BigInteger()),
    type_=JSONB(),
)
_operation_evaluation_page_statement = select(_operation_evaluation_page_function)


def prepare_operation_evaluation_page(
    *,
    project_id: ProjectId,
    evaluation_id: int,
    view: str,
    facet: str | None,
    direction: str | None,
    cursor: str | None,
    limit: int,
    max_bytes: int,
    projection_context: PreparedRelease | None = None,
) -> Select[JsonValue]:
    _request = _operation_evaluation_pageRequest(
        project_id=project_id,
        evaluation_id=evaluation_id,
        view=view,
        facet=facet,
        direction=direction,
        cursor=cursor,
        limit=limit,
        max_bytes=max_bytes,
    )
    if projection_context is not None:
        require_call_context(
            projection_context,
            "reference_operation_grade",
            "operation_evaluation_page",
            OPERATION_EVALUATION_PAGE_CONTRACT_DIGEST,
        )
    return cast(
        Select[JsonValue],
        _operation_evaluation_page_statement.params(
            **{
                "project_id": _request.project_id,
                "evaluation_id": _request.evaluation_id,
                "view": _request.view,
                "facet": _request.facet,
                "direction": _request.direction,
                "cursor": _request.cursor,
                "limit": _request.limit,
                "max_bytes": _request.max_bytes,
            }
        ),
    )


_operation_evaluation_page_adapter = TypeAdapter(JsonValue)


def materialize_operation_evaluation_page(row: tuple[JsonValue]) -> JsonValue:
    with native_result_scope("reference_operation_grade", "operation_evaluation_page", "result"):
        checked = _operation_evaluation_page_adapter.validate_python(row[0], strict=True)
        return checked


def operation_evaluation_page(
    conn: Connection,
    *,
    project_id: ProjectId,
    evaluation_id: int,
    view: str,
    facet: str | None,
    direction: str | None,
    cursor: str | None,
    limit: int,
    max_bytes: int,
    projection_context: PreparedRelease | None = None,
) -> JsonValue:
    _statement = prepare_operation_evaluation_page(
        project_id=project_id,
        evaluation_id=evaluation_id,
        view=view,
        facet=facet,
        direction=direction,
        cursor=cursor,
        limit=limit,
        max_bytes=max_bytes,
        projection_context=projection_context,
    )
    _native_result = conn.execute(_statement)
    with native_result_scope("reference_operation_grade", "operation_evaluation_page"):
        row = _native_result.one()
        return materialize_operation_evaluation_page(row)


PUBLISH_CHARACTERIZATION_CONTRACT_DIGEST = (
    "f513225ca5586371e0c1df6e98f8c3e52b8abd0c4c9040af5bda4a3ec667e3bb"
)


class _publish_characterizationRequest(OperationResult):
    task_id: Annotated[
        TaskId, Field(ge=TaskId(-9223372036854775808), le=TaskId(9223372036854775807))
    ]
    attempt: Annotated[
        TaskAttempt,
        Field(ge=TaskAttempt(-9223372036854775808), le=TaskAttempt(9223372036854775807)),
    ]
    holder: str
    layer: JsonValue | None
    view: JsonValue | None
    cost: JsonValue | None


_publish_characterization_function = func.ops.publish_characterization(
    bindparam("task_id", type_=BigInteger()),
    bindparam("attempt", type_=BigInteger()),
    bindparam("holder", type_=Text()),
    bindparam("layer", type_=JSONB(none_as_null=True)),
    bindparam("view", type_=JSONB(none_as_null=True)),
    bindparam("cost", type_=JSONB(none_as_null=True)),
    type_=JSONB(),
)
_publish_characterization_statement = select(_publish_characterization_function)


def prepare_publish_characterization(
    *,
    task_id: TaskId,
    attempt: TaskAttempt,
    holder: str,
    layer: JsonValue | None,
    view: JsonValue | None,
    cost: JsonValue | None,
    projection_context: PreparedRelease | None = None,
) -> Select[JsonValue]:
    _request = _publish_characterizationRequest(
        task_id=task_id,
        attempt=attempt,
        holder=holder,
        layer=layer,
        view=view,
        cost=cost,
    )
    if projection_context is not None:
        require_call_context(
            projection_context,
            "publish_characterization",
            "publish_characterization",
            PUBLISH_CHARACTERIZATION_CONTRACT_DIGEST,
        )
    return cast(
        Select[JsonValue],
        _publish_characterization_statement.params(
            **{
                "task_id": _request.task_id,
                "attempt": _request.attempt,
                "holder": _request.holder,
                "layer": _request.layer,
                "view": _request.view,
                "cost": _request.cost,
            }
        ),
    )


_publish_characterization_adapter = TypeAdapter(JsonValue)


def materialize_publish_characterization(row: tuple[JsonValue]) -> JsonValue:
    with native_result_scope("publish_characterization", "publish_characterization", "result"):
        checked = _publish_characterization_adapter.validate_python(row[0], strict=True)
        return checked


def publish_characterization(
    conn: Connection,
    *,
    task_id: TaskId,
    attempt: TaskAttempt,
    holder: str,
    layer: JsonValue | None,
    view: JsonValue | None,
    cost: JsonValue | None,
    projection_context: PreparedRelease | None = None,
) -> JsonValue:
    _statement = prepare_publish_characterization(
        task_id=task_id,
        attempt=attempt,
        holder=holder,
        layer=layer,
        view=view,
        cost=cost,
        projection_context=projection_context,
    )
    _native_result = conn.execute(_statement)
    with native_result_scope("publish_characterization", "publish_characterization"):
        row = _native_result.one()
        return materialize_publish_characterization(row)


READ_CHARACTERIZATION_PRODUCT_CONTRACT_DIGEST = (
    "c6b78cd5cfac35fd893ed3046e414152e5a97df16ef3b90855dd9e9a5f3a4d3d"
)


class _read_characterization_productRequest(OperationResult):
    task_id: Annotated[int, Field(ge=-9223372036854775808, le=9223372036854775807)]
    product_key: str
    content_digest: str
    kind: str
    run_id: (
        Annotated[RunId, Field(ge=RunId(-9223372036854775808), le=RunId(9223372036854775807))]
        | None
    )
    max_bytes: Annotated[int, Field(ge=-9223372036854775808, le=9223372036854775807)]


_read_characterization_product_function = func.ops.read_characterization_product(
    bindparam("task_id", type_=BigInteger()),
    bindparam("product_key", type_=Text()),
    bindparam("content_digest", type_=Text()),
    bindparam("kind", type_=Text()),
    bindparam("run_id", type_=BigInteger()),
    bindparam("max_bytes", type_=BigInteger()),
    type_=JSONB(),
)
_read_characterization_product_statement = select(_read_characterization_product_function)


def prepare_read_characterization_product(
    *,
    task_id: int,
    product_key: str,
    content_digest: str,
    kind: str,
    run_id: RunId | None,
    max_bytes: int,
    projection_context: PreparedRelease | None = None,
) -> Select[JsonValue]:
    _request = _read_characterization_productRequest(
        task_id=task_id,
        product_key=product_key,
        content_digest=content_digest,
        kind=kind,
        run_id=run_id,
        max_bytes=max_bytes,
    )
    if projection_context is not None:
        require_call_context(
            projection_context,
            "read_characterization",
            "read_characterization_product",
            READ_CHARACTERIZATION_PRODUCT_CONTRACT_DIGEST,
        )
    return cast(
        Select[JsonValue],
        _read_characterization_product_statement.params(
            **{
                "task_id": _request.task_id,
                "product_key": _request.product_key,
                "content_digest": _request.content_digest,
                "kind": _request.kind,
                "run_id": _request.run_id,
                "max_bytes": _request.max_bytes,
            }
        ),
    )


_read_characterization_product_adapter = TypeAdapter(JsonValue)


def materialize_read_characterization_product(row: tuple[JsonValue]) -> JsonValue:
    with native_result_scope("read_characterization", "read_characterization_product", "result"):
        checked = _read_characterization_product_adapter.validate_python(row[0], strict=True)
        return checked


def read_characterization_product(
    conn: Connection,
    *,
    task_id: int,
    product_key: str,
    content_digest: str,
    kind: str,
    run_id: RunId | None,
    max_bytes: int,
    projection_context: PreparedRelease | None = None,
) -> JsonValue:
    _statement = prepare_read_characterization_product(
        task_id=task_id,
        product_key=product_key,
        content_digest=content_digest,
        kind=kind,
        run_id=run_id,
        max_bytes=max_bytes,
        projection_context=projection_context,
    )
    _native_result = conn.execute(_statement)
    with native_result_scope("read_characterization", "read_characterization_product"):
        row = _native_result.one()
        return materialize_read_characterization_product(row)


READ_CHARACTERIZATION_LAYER_MANIFEST_CONTRACT_DIGEST = (
    "645fbbb8db3d39417d433449394e6543ea853ecbf5d4d07a7ec48d943e73e82d"
)


class _read_characterization_layer_manifestRequest(OperationResult):
    task_id: Annotated[int, Field(ge=-9223372036854775808, le=9223372036854775807)]
    product_key: str
    content_digest: str
    run_id: (
        Annotated[RunId, Field(ge=RunId(-9223372036854775808), le=RunId(9223372036854775807))]
        | None
    )
    max_bytes: Annotated[int, Field(ge=-9223372036854775808, le=9223372036854775807)]


_read_characterization_layer_manifest_function = func.ops.read_characterization_layer_manifest(
    bindparam("task_id", type_=BigInteger()),
    bindparam("product_key", type_=Text()),
    bindparam("content_digest", type_=Text()),
    bindparam("run_id", type_=BigInteger()),
    bindparam("max_bytes", type_=BigInteger()),
    type_=JSONB(),
)
_read_characterization_layer_manifest_statement = select(
    _read_characterization_layer_manifest_function
)


def prepare_read_characterization_layer_manifest(
    *,
    task_id: int,
    product_key: str,
    content_digest: str,
    run_id: RunId | None,
    max_bytes: int,
    projection_context: PreparedRelease | None = None,
) -> Select[JsonValue]:
    _request = _read_characterization_layer_manifestRequest(
        task_id=task_id,
        product_key=product_key,
        content_digest=content_digest,
        run_id=run_id,
        max_bytes=max_bytes,
    )
    if projection_context is not None:
        require_call_context(
            projection_context,
            "read_characterization",
            "read_characterization_layer_manifest",
            READ_CHARACTERIZATION_LAYER_MANIFEST_CONTRACT_DIGEST,
        )
    return cast(
        Select[JsonValue],
        _read_characterization_layer_manifest_statement.params(
            **{
                "task_id": _request.task_id,
                "product_key": _request.product_key,
                "content_digest": _request.content_digest,
                "run_id": _request.run_id,
                "max_bytes": _request.max_bytes,
            }
        ),
    )


_read_characterization_layer_manifest_adapter = TypeAdapter(JsonValue)


def materialize_read_characterization_layer_manifest(row: tuple[JsonValue]) -> JsonValue:
    with native_result_scope(
        "read_characterization", "read_characterization_layer_manifest", "result"
    ):
        checked = _read_characterization_layer_manifest_adapter.validate_python(row[0], strict=True)
        return checked


def read_characterization_layer_manifest(
    conn: Connection,
    *,
    task_id: int,
    product_key: str,
    content_digest: str,
    run_id: RunId | None,
    max_bytes: int,
    projection_context: PreparedRelease | None = None,
) -> JsonValue:
    _statement = prepare_read_characterization_layer_manifest(
        task_id=task_id,
        product_key=product_key,
        content_digest=content_digest,
        run_id=run_id,
        max_bytes=max_bytes,
        projection_context=projection_context,
    )
    _native_result = conn.execute(_statement)
    with native_result_scope("read_characterization", "read_characterization_layer_manifest"):
        row = _native_result.one()
        return materialize_read_characterization_layer_manifest(row)


READ_CHARACTERIZATION_MEMBERSHIPS_CONTRACT_DIGEST = (
    "9df951d7c81d53cc3de8c3e416c05776a1da8af99357baf92f4ee3a9897cd87c"
)


class _read_characterization_membershipsRequest(OperationResult):
    task_id: Annotated[int, Field(ge=-9223372036854775808, le=9223372036854775807)]
    product_key: str
    content_digest: str
    groups: JsonValue
    run_id: (
        Annotated[RunId, Field(ge=RunId(-9223372036854775808), le=RunId(9223372036854775807))]
        | None
    )
    after: JsonValue | None
    layer_key: str | None
    limit: Annotated[int, Field(ge=-9223372036854775808, le=9223372036854775807)]
    max_bytes: Annotated[int, Field(ge=-9223372036854775808, le=9223372036854775807)]


_read_characterization_memberships_function = func.ops.read_characterization_memberships(
    bindparam("task_id", type_=BigInteger()),
    bindparam("product_key", type_=Text()),
    bindparam("content_digest", type_=Text()),
    bindparam("groups", type_=JSONB()),
    bindparam("run_id", type_=BigInteger()),
    bindparam("after", type_=JSONB(none_as_null=True)),
    bindparam("layer_key", type_=Text()),
    bindparam("limit", type_=BigInteger()),
    bindparam("max_bytes", type_=BigInteger()),
    type_=JSONB(),
)
_read_characterization_memberships_statement = select(_read_characterization_memberships_function)


def prepare_read_characterization_memberships(
    *,
    task_id: int,
    product_key: str,
    content_digest: str,
    groups: JsonValue,
    run_id: RunId | None,
    after: JsonValue | None,
    layer_key: str | None,
    limit: int,
    max_bytes: int,
    projection_context: PreparedRelease | None = None,
) -> Select[JsonValue]:
    _request = _read_characterization_membershipsRequest(
        task_id=task_id,
        product_key=product_key,
        content_digest=content_digest,
        groups=groups,
        run_id=run_id,
        after=after,
        layer_key=layer_key,
        limit=limit,
        max_bytes=max_bytes,
    )
    if projection_context is not None:
        require_call_context(
            projection_context,
            "read_characterization",
            "read_characterization_memberships",
            READ_CHARACTERIZATION_MEMBERSHIPS_CONTRACT_DIGEST,
        )
    return cast(
        Select[JsonValue],
        _read_characterization_memberships_statement.params(
            **{
                "task_id": _request.task_id,
                "product_key": _request.product_key,
                "content_digest": _request.content_digest,
                "groups": _request.groups,
                "run_id": _request.run_id,
                "after": _request.after,
                "layer_key": _request.layer_key,
                "limit": _request.limit,
                "max_bytes": _request.max_bytes,
            }
        ),
    )


_read_characterization_memberships_adapter = TypeAdapter(JsonValue)


def materialize_read_characterization_memberships(row: tuple[JsonValue]) -> JsonValue:
    with native_result_scope(
        "read_characterization", "read_characterization_memberships", "result"
    ):
        checked = _read_characterization_memberships_adapter.validate_python(row[0], strict=True)
        return checked


def read_characterization_memberships(
    conn: Connection,
    *,
    task_id: int,
    product_key: str,
    content_digest: str,
    groups: JsonValue,
    run_id: RunId | None,
    after: JsonValue | None,
    layer_key: str | None,
    limit: int,
    max_bytes: int,
    projection_context: PreparedRelease | None = None,
) -> JsonValue:
    _statement = prepare_read_characterization_memberships(
        task_id=task_id,
        product_key=product_key,
        content_digest=content_digest,
        groups=groups,
        run_id=run_id,
        after=after,
        layer_key=layer_key,
        limit=limit,
        max_bytes=max_bytes,
        projection_context=projection_context,
    )
    _native_result = conn.execute(_statement)
    with native_result_scope("read_characterization", "read_characterization_memberships"):
        row = _native_result.one()
        return materialize_read_characterization_memberships(row)


READ_CHARACTERIZATION_NODES_CONTRACT_DIGEST = (
    "e28eb4e29afe9de4d0c1e23c5ecbf546f1c11ec726f7d89235f3c02a8abacda4"
)


class _read_characterization_nodesRequest(OperationResult):
    task_id: Annotated[int, Field(ge=-9223372036854775808, le=9223372036854775807)]
    product_key: str
    content_digest: str
    kind: str
    selectors: JsonValue
    run_id: (
        Annotated[RunId, Field(ge=RunId(-9223372036854775808), le=RunId(9223372036854775807))]
        | None
    )
    after: JsonValue | None
    limit: Annotated[int, Field(ge=-9223372036854775808, le=9223372036854775807)]
    max_bytes: Annotated[int, Field(ge=-9223372036854775808, le=9223372036854775807)]


_read_characterization_nodes_function = func.ops.read_characterization_nodes(
    bindparam("task_id", type_=BigInteger()),
    bindparam("product_key", type_=Text()),
    bindparam("content_digest", type_=Text()),
    bindparam("kind", type_=Text()),
    bindparam("selectors", type_=JSONB()),
    bindparam("run_id", type_=BigInteger()),
    bindparam("after", type_=JSONB(none_as_null=True)),
    bindparam("limit", type_=BigInteger()),
    bindparam("max_bytes", type_=BigInteger()),
    type_=JSONB(),
)
_read_characterization_nodes_statement = select(_read_characterization_nodes_function)


def prepare_read_characterization_nodes(
    *,
    task_id: int,
    product_key: str,
    content_digest: str,
    kind: str,
    selectors: JsonValue,
    run_id: RunId | None,
    after: JsonValue | None,
    limit: int,
    max_bytes: int,
    projection_context: PreparedRelease | None = None,
) -> Select[JsonValue]:
    _request = _read_characterization_nodesRequest(
        task_id=task_id,
        product_key=product_key,
        content_digest=content_digest,
        kind=kind,
        selectors=selectors,
        run_id=run_id,
        after=after,
        limit=limit,
        max_bytes=max_bytes,
    )
    if projection_context is not None:
        require_call_context(
            projection_context,
            "read_characterization",
            "read_characterization_nodes",
            READ_CHARACTERIZATION_NODES_CONTRACT_DIGEST,
        )
    return cast(
        Select[JsonValue],
        _read_characterization_nodes_statement.params(
            **{
                "task_id": _request.task_id,
                "product_key": _request.product_key,
                "content_digest": _request.content_digest,
                "kind": _request.kind,
                "selectors": _request.selectors,
                "run_id": _request.run_id,
                "after": _request.after,
                "limit": _request.limit,
                "max_bytes": _request.max_bytes,
            }
        ),
    )


_read_characterization_nodes_adapter = TypeAdapter(JsonValue)


def materialize_read_characterization_nodes(row: tuple[JsonValue]) -> JsonValue:
    with native_result_scope("read_characterization", "read_characterization_nodes", "result"):
        checked = _read_characterization_nodes_adapter.validate_python(row[0], strict=True)
        return checked


def read_characterization_nodes(
    conn: Connection,
    *,
    task_id: int,
    product_key: str,
    content_digest: str,
    kind: str,
    selectors: JsonValue,
    run_id: RunId | None,
    after: JsonValue | None,
    limit: int,
    max_bytes: int,
    projection_context: PreparedRelease | None = None,
) -> JsonValue:
    _statement = prepare_read_characterization_nodes(
        task_id=task_id,
        product_key=product_key,
        content_digest=content_digest,
        kind=kind,
        selectors=selectors,
        run_id=run_id,
        after=after,
        limit=limit,
        max_bytes=max_bytes,
        projection_context=projection_context,
    )
    _native_result = conn.execute(_statement)
    with native_result_scope("read_characterization", "read_characterization_nodes"):
        row = _native_result.one()
        return materialize_read_characterization_nodes(row)


READ_PRIMARY_CHARACTERIZATION_CONTRACT_DIGEST = (
    "f8572de499d8022ed287070c980a6dcac497597a47f417eb50a25bb3d8999ef1"
)


class _read_primary_characterizationRequest(OperationResult):
    run_id: Annotated[RunId, Field(ge=RunId(-9223372036854775808), le=RunId(9223372036854775807))]
    source_view_id: Annotated[
        SourceViewId,
        Field(ge=SourceViewId(-9223372036854775808), le=SourceViewId(9223372036854775807)),
    ]
    references: JsonValue
    max_bytes: Annotated[int, Field(ge=-9223372036854775808, le=9223372036854775807)]


_read_primary_characterization_function = func.ops.read_primary_characterization(
    bindparam("run_id", type_=BigInteger()),
    bindparam("source_view_id", type_=BigInteger()),
    bindparam("references", type_=JSONB()),
    bindparam("max_bytes", type_=BigInteger()),
    type_=JSONB(),
)
_read_primary_characterization_statement = select(_read_primary_characterization_function)


def prepare_read_primary_characterization(
    *,
    run_id: RunId,
    source_view_id: SourceViewId,
    references: JsonValue,
    max_bytes: int,
    projection_context: PreparedRelease | None = None,
) -> Select[JsonValue]:
    _request = _read_primary_characterizationRequest(
        run_id=run_id,
        source_view_id=source_view_id,
        references=references,
        max_bytes=max_bytes,
    )
    if projection_context is not None:
        require_call_context(
            projection_context,
            "read_characterization",
            "read_primary_characterization",
            READ_PRIMARY_CHARACTERIZATION_CONTRACT_DIGEST,
        )
    return cast(
        Select[JsonValue],
        _read_primary_characterization_statement.params(
            **{
                "run_id": _request.run_id,
                "source_view_id": _request.source_view_id,
                "references": _request.references,
                "max_bytes": _request.max_bytes,
            }
        ),
    )


_read_primary_characterization_adapter = TypeAdapter(JsonValue)


def materialize_read_primary_characterization(row: tuple[JsonValue]) -> JsonValue:
    with native_result_scope("read_characterization", "read_primary_characterization", "result"):
        checked = _read_primary_characterization_adapter.validate_python(row[0], strict=True)
        return checked


def read_primary_characterization(
    conn: Connection,
    *,
    run_id: RunId,
    source_view_id: SourceViewId,
    references: JsonValue,
    max_bytes: int,
    projection_context: PreparedRelease | None = None,
) -> JsonValue:
    _statement = prepare_read_primary_characterization(
        run_id=run_id,
        source_view_id=source_view_id,
        references=references,
        max_bytes=max_bytes,
        projection_context=projection_context,
    )
    _native_result = conn.execute(_statement)
    with native_result_scope("read_characterization", "read_primary_characterization"):
        row = _native_result.one()
        return materialize_read_primary_characterization(row)


READ_CHARACTERIZATION_INVENTORY_CONTRACT_DIGEST = (
    "a20732de4c262a68d21fd310fbe33d39b6b982c464256fe859832ae4a10c75de"
)


class _read_characterization_inventoryRequest(OperationResult):
    run_id: Annotated[RunId, Field(ge=RunId(-9223372036854775808), le=RunId(9223372036854775807))]
    after_task: (
        Annotated[TaskId, Field(ge=TaskId(-9223372036854775808), le=TaskId(9223372036854775807))]
        | None
    )
    after_key: str | None
    limit: Annotated[int, Field(ge=-9223372036854775808, le=9223372036854775807)]
    max_bytes: Annotated[int, Field(ge=-9223372036854775808, le=9223372036854775807)]


_read_characterization_inventory_function = func.ops.read_characterization_inventory(
    bindparam("run_id", type_=BigInteger()),
    bindparam("after_task", type_=BigInteger()),
    bindparam("after_key", type_=Text()),
    bindparam("limit", type_=BigInteger()),
    bindparam("max_bytes", type_=BigInteger()),
    type_=JSONB(),
)
_read_characterization_inventory_statement = select(_read_characterization_inventory_function)


def prepare_read_characterization_inventory(
    *,
    run_id: RunId,
    after_task: TaskId | None,
    after_key: str | None,
    limit: int,
    max_bytes: int,
    projection_context: PreparedRelease | None = None,
) -> Select[JsonValue]:
    _request = _read_characterization_inventoryRequest(
        run_id=run_id,
        after_task=after_task,
        after_key=after_key,
        limit=limit,
        max_bytes=max_bytes,
    )
    if projection_context is not None:
        require_call_context(
            projection_context,
            "read_characterization_inventory",
            "read_characterization_inventory",
            READ_CHARACTERIZATION_INVENTORY_CONTRACT_DIGEST,
        )
    return cast(
        Select[JsonValue],
        _read_characterization_inventory_statement.params(
            **{
                "run_id": _request.run_id,
                "after_task": _request.after_task,
                "after_key": _request.after_key,
                "limit": _request.limit,
                "max_bytes": _request.max_bytes,
            }
        ),
    )


_read_characterization_inventory_adapter = TypeAdapter(JsonValue)


def materialize_read_characterization_inventory(row: tuple[JsonValue]) -> JsonValue:
    with native_result_scope(
        "read_characterization_inventory", "read_characterization_inventory", "result"
    ):
        checked = _read_characterization_inventory_adapter.validate_python(row[0], strict=True)
        return checked


def read_characterization_inventory(
    conn: Connection,
    *,
    run_id: RunId,
    after_task: TaskId | None,
    after_key: str | None,
    limit: int,
    max_bytes: int,
    projection_context: PreparedRelease | None = None,
) -> JsonValue:
    _statement = prepare_read_characterization_inventory(
        run_id=run_id,
        after_task=after_task,
        after_key=after_key,
        limit=limit,
        max_bytes=max_bytes,
        projection_context=projection_context,
    )
    _native_result = conn.execute(_statement)
    with native_result_scope("read_characterization_inventory", "read_characterization_inventory"):
        row = _native_result.one()
        return materialize_read_characterization_inventory(row)


CALL_CONTRACT_DIGEST = "f9efc77accb5676640eb7ebb363aed41f852b0d46cf37cd13fcde2c6d67762b7"
