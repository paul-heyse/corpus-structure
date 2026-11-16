"""Generated from execution call correspondences; do not edit."""

from __future__ import annotations

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
from ._operation_ids import MethodConfigId as MethodConfigId
from ._operation_ids import MethodId as MethodId
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
