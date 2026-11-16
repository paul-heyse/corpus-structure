"""Generated from authenticated fixed-call assets; do not edit."""

from __future__ import annotations

from collections.abc import Sequence
from decimal import Decimal
from typing import (
    Annotated,
    Protocol,
    cast,
)

from pydantic import Field, JsonValue, TypeAdapter
from sqlalchemy import (
    ARRAY,
    BigInteger,
    Boolean,
    Column,
    Connection,
    Integer,
    Numeric,
    Select,
    Text,
    bindparam,
    column,
    func,
    select,
)
from sqlalchemy.dialects.postgresql import BYTEA, JSONB

from corpus_structure.semantic.identifiers import ContentDigest as ContentDigest
from corpus_structure.semantic.identifiers import ProductKey as ProductKey
from corpus_structure.semantic.identifiers import ReleaseId as ReleaseId
from corpus_structure.semantic.identifiers import TaskAttempt as TaskAttempt
from corpus_structure.semantic.identifiers import TaskId as TaskId

from ._pdf_native_ids import PdfFrozenBuildKind as PdfFrozenBuildKind
from ._pdf_native_ids import PdfPublishedRevisionKind as PdfPublishedRevisionKind
from ._pdf_native_ids import PdfRecordCompanionFamily as PdfRecordCompanionFamily
from ._pdf_native_ids import (
    PdfSourceViewPublicationMembership as PdfSourceViewPublicationMembership,
)
from ._pdf_native_ids import PdfStageBuildState as PdfStageBuildState
from ._pdf_native_ids import PublishedSectionNodeRowRole as PublishedSectionNodeRowRole
from .operation_value_types import (
    NativeResultViolation,
    NativeRowResult,
    OperationResult,
    native_result_scope,
)
from .pdf_domain import require_pdf_call_context as require_call_context
from .types import PreparedRelease


def _required[T](value: T | None, field: str, result_class: str, operation: str) -> T:
    if value is None:
        raise NativeResultViolation(operation, result_class, field)
    return value


ABANDON_PDF_BUILD_CONTRACT_DIGEST = (
    "111a200b490f3bcc284e4389af37153b8b7e85eea5aae4bd78cd4121e854c8cb"
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


PREPARE_PDF_STAGE_CONTRACT_DIGEST = (
    "13fcd5aa91e2ac3d7c3639c21773f78a4081c80a68a6469aea99cef5c8bc310c"
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


ADOPT_PDF_BATCH_CONTRACT_DIGEST = "6dbcdb5676bde8a2dc734ffef8ed5d66d4a306f8f411aee15912497899b9c836"


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


ADOPT_PDF_COMPANION_CONTRACT_DIGEST = (
    "35637088837b67d4adfb3f8251230917baf3593095288334b2af3875f49f8030"
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


BEGIN_PDF_BUILD_CONTRACT_DIGEST = "a9068499d9af498f56d07fa75dfdfe0c056cf70fe8a71ff43886203be7a9b1e8"


class PdfStageBuild(NativeRowResult):
    build_id: str
    task_id: TaskId
    release_id: str
    source_digest: str
    recipe_digest: str
    schema_digest: str
    replay_key: str
    attempt: TaskAttempt
    holder: str
    state: PdfStageBuildState


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
    task_id: Column[TaskId]
    release_id: Column[str]
    source_digest: Column[str]
    recipe_digest: Column[str]
    schema_digest: Column[str]
    replay_key: Column[str]
    attempt: Column[TaskAttempt]
    holder: Column[str]
    state: Column[PdfStageBuildState]


_begin_pdf_build_columns = cast(_begin_pdf_buildColumns, _begin_pdf_build_function.c)
_begin_pdf_build_statement = select(
    _begin_pdf_build_columns.build_id,
    _begin_pdf_build_columns.task_id,
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
    row: tuple[str, int, str, str, str, str, str, int, str, str],
) -> PdfStageBuild:
    with native_result_scope("begin_pdf_build", "PdfStageBuild"):
        return PdfStageBuild(
            build_id=row[0],
            task_id=TaskId(row[1]),
            release_id=row[2],
            source_digest=row[3],
            recipe_digest=row[4],
            schema_digest=row[5],
            replay_key=row[6],
            attempt=TaskAttempt(row[7]),
            holder=row[8],
            state=cast(PdfStageBuildState, row[9]),
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
) -> Select[str, TaskId, str, str, str, str, str, TaskAttempt, str, PdfStageBuildState]:
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
    return cast(
        Select[str, TaskId, str, str, str, str, str, TaskAttempt, str, PdfStageBuildState],
        _begin_pdf_build_statement.params(
            **{
                "task_id": _request.task_id,
                "attempt": _request.attempt,
                "holder": _request.holder,
                "source_digest": _request.source_digest,
                "recipe_digest": _request.recipe_digest,
                "schema_digest": _request.schema_digest,
                "replay_key": _request.replay_key,
            }
        ),
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


FREEZE_PDF_BUILD_CONTRACT_DIGEST = (
    "8ba06f838ad3fe59438428fd64ab260fd1eedde5e6588c99994247ee2d7a43c4"
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


LOOKUP_PDF_BUILD_CONTRACT_DIGEST = (
    "d21eabd588ac660fee9439f45ed22e76147e0df76311e91bc0532a13a2890b03"
)


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
    task_id: Column[TaskId]
    release_id: Column[str]
    source_digest: Column[str]
    recipe_digest: Column[str]
    schema_digest: Column[str]
    replay_key: Column[str]
    attempt: Column[TaskAttempt]
    holder: Column[str]
    state: Column[PdfStageBuildState]


_lookup_pdf_build_columns = cast(_lookup_pdf_buildColumns, _lookup_pdf_build_function.c)
_lookup_pdf_build_statement = select(
    _lookup_pdf_build_columns.build_id,
    _lookup_pdf_build_columns.task_id,
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
    row: tuple[str, int, str, str, str, str, str, int, str, str],
) -> PdfStageBuild:
    with native_result_scope("inspect_pdf_build", "PdfStageBuild"):
        return PdfStageBuild(
            build_id=row[0],
            task_id=TaskId(row[1]),
            release_id=row[2],
            source_digest=row[3],
            recipe_digest=row[4],
            schema_digest=row[5],
            replay_key=row[6],
            attempt=TaskAttempt(row[7]),
            holder=row[8],
            state=cast(PdfStageBuildState, row[9]),
        )


def prepare_lookup_pdf_build(
    *,
    task_id: TaskId,
    attempt: TaskAttempt,
    holder: str,
    replay_key: str,
    projection_context: PreparedRelease | None = None,
) -> Select[str, TaskId, str, str, str, str, str, TaskAttempt, str, PdfStageBuildState]:
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
    return cast(
        Select[str, TaskId, str, str, str, str, str, TaskAttempt, str, PdfStageBuildState],
        _lookup_pdf_build_statement.params(
            **{
                "task_id": _request.task_id,
                "attempt": _request.attempt,
                "holder": _request.holder,
                "replay_key": _request.replay_key,
            }
        ),
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
    "5a71e06b5f27c60a863bd696d8506a399b5bb60c259e741d750cead3a3ac1682"
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
    "9386899fcea4cf5fcd92ad0bb59face7cce69e53e852350a00ea718f791b99ae"
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
    "87f466b7823699abccb7c91e916fbba4b696188b83f8a4caa41465a56d822e8d"
)


class PdfPublishedRevision(NativeRowResult):
    build_id: str
    task_id: TaskId
    product_key: ProductKey
    logical_digest: ContentDigest
    release_id: ReleaseId
    source_digest: str
    schema_digest: str
    recipe_digest: str
    frozen_digest: str
    kind: PdfPublishedRevisionKind


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
    task_id: Column[TaskId]
    product_key: Column[ProductKey]
    logical_digest: Column[ContentDigest]
    release_id: Column[ReleaseId]
    source_digest: Column[str]
    schema_digest: Column[str]
    recipe_digest: Column[str]
    frozen_digest: Column[str]
    kind: Column[PdfPublishedRevisionKind]


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
            task_id=TaskId(row[1]),
            product_key=ProductKey(row[2]),
            logical_digest=ContentDigest(row[3]),
            release_id=ReleaseId(row[4]),
            source_digest=row[5],
            schema_digest=row[6],
            recipe_digest=row[7],
            frozen_digest=row[8],
            kind=cast(PdfPublishedRevisionKind, row[9]),
        )


def prepare_lookup_pdf_published_build(
    *,
    build_id: str,
    task_id: TaskId,
    attempt: TaskAttempt,
    holder: str,
    projection_context: PreparedRelease | None = None,
) -> Select[
    str, TaskId, ProductKey, ContentDigest, ReleaseId, str, str, str, str, PdfPublishedRevisionKind
]:
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
    return cast(
        Select[
            str,
            TaskId,
            ProductKey,
            ContentDigest,
            ReleaseId,
            str,
            str,
            str,
            str,
            PdfPublishedRevisionKind,
        ],
        _lookup_pdf_published_build_statement.params(
            **{
                "build_id": _request.build_id,
                "task_id": _request.task_id,
                "attempt": _request.attempt,
                "holder": _request.holder,
            }
        ),
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


INSPECT_PDF_PROGRESS_CONTRACT_DIGEST = (
    "5c2e9d4849d37b80e727f9e5fbc2b579397a0d24ec5ad769ce917439d53d09b8"
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


PREPARE_PDF_BUILD_CONTRACT_DIGEST = (
    "f70e8469cba61bac5235d478a5a3b59636e6d1c44b9e7e6f87387293c577ee3a"
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


PUBLISH_PDF_OBSERVATION_CONTRACT_DIGEST = (
    "cfb730ab2c3ad93121b42138cb76fdb532fc77e744a3011f8c9a6c0330501fa6"
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


READ_PUBLISHED_SECTIONS_CONTRACT_DIGEST = (
    "e50128ebbfb033bf1dda84af2741b72da17b1e13351ca506a3cb310b6b8ef754"
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
    "2883dc5028b762442e89a35c6e9bd38b211d80e2c7cc3db93672dc2d0a9f417f"
)


class PublishedSectionNodeRow(NativeRowResult):
    __json_fields__ = ("native_json",)
    role: PublishedSectionNodeRowRole
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
    role: Column[PublishedSectionNodeRowRole]
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
            role=cast(PublishedSectionNodeRowRole, row[0]),
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
) -> Select[
    PublishedSectionNodeRowRole,
    str,
    str,
    str,
    int,
    str,
    str | None,
    str | None,
    str,
    str | None,
    str,
]:
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
    return cast(
        Select[
            PublishedSectionNodeRowRole,
            str,
            str,
            str,
            int,
            str,
            str | None,
            str | None,
            str,
            str | None,
            str,
        ],
        _read_published_section_nodes_statement.params(
            **{
                "task_id": _request.task_id,
                "product_key": _request.product_key,
                "content_digest": _request.content_digest,
                "section": _request.section,
                "membership": _request.membership,
            }
        ),
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
    "b2ccadfdcf6389375aa672f0f825dd20d588fb6ac36cee4535b2c8e88095227b"
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
    return cast(
        Select[str, str, str, int, str, str | None, str | None, str, str | None, str],
        _read_published_items_statement.params(
            **{
                "task_id": _request.task_id,
                "product_key": _request.product_key,
                "content_digest": _request.content_digest,
                "pointers": _request.pointers,
            }
        ),
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
    "852ca6f615f1ccffd42e153ac60e8b57a27acfaccd76f5b1c52b09065a55b48f"
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
    return cast(
        Select[str, str, str, int, int, Decimal, Decimal, Decimal, Decimal, Decimal, Decimal, str],
        _read_published_region_statement.params(
            **{
                "task_id": _request.task_id,
                "product_key": _request.product_key,
                "content_digest": _request.content_digest,
                "pointer": _request.pointer,
                "region_index": _request.region_index,
            }
        ),
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
    "a17c4f8a2c0bfe9d381c506e481801cf75f388491abd42fc96922d4f38854600"
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
    "5ceb8990ba39f3eb418a011257f0d9625ad99a0d24baa41db4476760c0b420ab"
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
    "0232a6107725683050ecf36b3beef03d4856b2b1eaff511b76efb0590916b86c"
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
    return cast(
        Select[str, str, str, int, int, Decimal, Decimal, Decimal, Decimal, Decimal, Decimal, str],
        _read_published_regions_statement.params(
            **{
                "task_id": _request.task_id,
                "product_key": _request.product_key,
                "content_digest": _request.content_digest,
                "pointer": _request.pointer,
            }
        ),
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
    "1aa6879f252719e653685c525d4cfaa4a7c83751ee6dfb30d95663708276e231"
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
    return cast(
        Select[str, str, str, int, int, Decimal, Decimal, Decimal, Decimal, Decimal, Decimal, str],
        _read_published_region_batch_statement.params(
            **{
                "task_id": _request.task_id,
                "product_key": _request.product_key,
                "content_digest": _request.content_digest,
                "pointers": _request.pointers,
            }
        ),
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
    "8f62a532a6ccf5dcdbe90f946926b9337de4a2a1bb435122fab878e18c9b0cb8"
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
    "7b098a2066279b6c64db4221ca96d190fbb3ca649f4963e28714404a1f6f2e69"
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
    "3e6129a1add8f192276658659dfa2ad3abaded206fd25d05202a5fb6d65bdb01"
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
    "ed03132bbc1387c342f782e77bc66fa24d004ec91c8432739ad7df31bc571d97"
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
    "acfc625d733d449b1bb3ee74383d8456cea3e114e51cb354be2ceceda87be4ac"
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
    "af6dfd9c09d3e78aaf84d6944501cf6cad46d4ad7c223f2fa959e1e351b733fb"
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
    "c2239f1e05d1d064a9021a6531f3c929ac9b06703f410d447b92a4cf2a07efdd"
)


class _read_pdf_selected_source_eventsRequest(OperationResult):
    project_id: str
    demand_id: str
    read_id: str
    use_id: str
    product_id: str
    derivation_id: str
    section: str
    membership: str
    policy: str


_read_pdf_selected_source_events_function = func.ops.read_pdf_selected_source_events(
    bindparam("project_id", type_=Text()),
    bindparam("demand_id", type_=Text()),
    bindparam("read_id", type_=Text()),
    bindparam("use_id", type_=Text()),
    bindparam("product_id", type_=Text()),
    bindparam("derivation_id", type_=Text()),
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
    project_id: str,
    demand_id: str,
    read_id: str,
    use_id: str,
    product_id: str,
    derivation_id: str,
    section: str,
    membership: str,
    policy: str,
    projection_context: PreparedRelease | None = None,
) -> Select[str]:
    _request = _read_pdf_selected_source_eventsRequest(
        project_id=project_id,
        demand_id=demand_id,
        read_id=read_id,
        use_id=use_id,
        product_id=product_id,
        derivation_id=derivation_id,
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
            "demand_id": _request.demand_id,
            "read_id": _request.read_id,
            "use_id": _request.use_id,
            "product_id": _request.product_id,
            "derivation_id": _request.derivation_id,
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
    project_id: str,
    demand_id: str,
    read_id: str,
    use_id: str,
    product_id: str,
    derivation_id: str,
    section: str,
    membership: str,
    policy: str,
    projection_context: PreparedRelease | None = None,
) -> tuple[NativeJsonEnvelope, ...]:
    _statement = prepare_read_pdf_selected_source_events(
        project_id=project_id,
        demand_id=demand_id,
        read_id=read_id,
        use_id=use_id,
        product_id=product_id,
        derivation_id=derivation_id,
        section=section,
        membership=membership,
        policy=policy,
        projection_context=projection_context,
    )
    _native_result = conn.execute(_statement)
    with native_result_scope("read_native_source", "NativeJsonEnvelope"):
        return tuple(materialize_read_pdf_selected_source_events(row) for row in _native_result)


READ_PDF_PUBLISHED_REVISION_CONTRACT_DIGEST = (
    "dabd826df32d4859206ec1424dbaa57328fb812f572f675b890d745c9052165c"
)


class _read_pdf_published_revisionRequest(OperationResult):
    task_id: Annotated[
        TaskId, Field(ge=TaskId(-9223372036854775808), le=TaskId(9223372036854775807))
    ]
    product_key: ProductKey
    logical_digest: ContentDigest


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
    task_id: Column[TaskId]
    product_key: Column[ProductKey]
    logical_digest: Column[ContentDigest]
    release_id: Column[ReleaseId]
    source_digest: Column[str]
    schema_digest: Column[str]
    recipe_digest: Column[str]
    frozen_digest: Column[str]
    kind: Column[PdfPublishedRevisionKind]


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
            task_id=TaskId(row[1]),
            product_key=ProductKey(row[2]),
            logical_digest=ContentDigest(row[3]),
            release_id=ReleaseId(row[4]),
            source_digest=row[5],
            schema_digest=row[6],
            recipe_digest=row[7],
            frozen_digest=row[8],
            kind=cast(PdfPublishedRevisionKind, row[9]),
        )


def prepare_read_pdf_published_revision(
    *,
    task_id: TaskId,
    product_key: ProductKey,
    logical_digest: ContentDigest,
    projection_context: PreparedRelease | None = None,
) -> Select[
    str, TaskId, ProductKey, ContentDigest, ReleaseId, str, str, str, str, PdfPublishedRevisionKind
]:
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
    return cast(
        Select[
            str,
            TaskId,
            ProductKey,
            ContentDigest,
            ReleaseId,
            str,
            str,
            str,
            str,
            PdfPublishedRevisionKind,
        ],
        _read_pdf_published_revision_statement.params(
            **{
                "task_id": _request.task_id,
                "product_key": _request.product_key,
                "logical_digest": _request.logical_digest,
            }
        ),
    )


materialize_read_pdf_published_revision = _read_pdf_published_revision_result


def read_pdf_published_revision(
    conn: Connection,
    *,
    task_id: TaskId,
    product_key: ProductKey,
    logical_digest: ContentDigest,
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


READ_PDF_MATERIALIZATION_BOUND_CONTRACT_DIGEST = (
    "3b23fddbd0d6f6a24923bcb6f40d70c2c68e4049b1f553cf21579ad4634037e0"
)


class _read_pdf_materialization_boundRequest(OperationResult):
    task_id: Annotated[
        TaskId, Field(ge=TaskId(-9223372036854775808), le=TaskId(9223372036854775807))
    ]
    product_key: ProductKey
    content_digest: ContentDigest


_read_pdf_materialization_bound_function = func.ops.read_pdf_materialization_bound(
    bindparam("task_id", type_=BigInteger()),
    bindparam("product_key", type_=Text()),
    bindparam("content_digest", type_=Text()),
    type_=BigInteger(),
)
_read_pdf_materialization_bound_statement = select(_read_pdf_materialization_bound_function)


def prepare_read_pdf_materialization_bound(
    *,
    task_id: TaskId,
    product_key: ProductKey,
    content_digest: ContentDigest,
    projection_context: PreparedRelease | None = None,
) -> Select[int]:
    _request = _read_pdf_materialization_boundRequest(
        task_id=task_id,
        product_key=product_key,
        content_digest=content_digest,
    )
    if projection_context is not None:
        require_call_context(
            projection_context,
            "read_pdf_product",
            "read_pdf_materialization_bound",
            READ_PDF_MATERIALIZATION_BOUND_CONTRACT_DIGEST,
        )
    return _read_pdf_materialization_bound_statement.params(
        **{
            "task_id": _request.task_id,
            "product_key": _request.product_key,
            "content_digest": _request.content_digest,
        }
    )


_read_pdf_materialization_bound_adapter = TypeAdapter(int)


def materialize_read_pdf_materialization_bound(row: tuple[int]) -> int:
    with native_result_scope("read_pdf_product", "read_pdf_materialization_bound", "byte_bound"):
        checked = _read_pdf_materialization_bound_adapter.validate_python(row[0], strict=True)
        return checked


def read_pdf_materialization_bound(
    conn: Connection,
    *,
    task_id: TaskId,
    product_key: ProductKey,
    content_digest: ContentDigest,
    projection_context: PreparedRelease | None = None,
) -> int:
    _statement = prepare_read_pdf_materialization_bound(
        task_id=task_id,
        product_key=product_key,
        content_digest=content_digest,
        projection_context=projection_context,
    )
    _native_result = conn.execute(_statement)
    with native_result_scope("read_pdf_product", "read_pdf_materialization_bound"):
        row = _native_result.one()
        return materialize_read_pdf_materialization_bound(row)


READ_PDF_PUBLISHED_VALIDATION_CONTRACT_DIGEST = (
    "13180d57c31deb9fcc7f562cfa793084031d21cee7d52f0e51403cd3721ff567"
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


RESUME_PDF_BUILD_CONTRACT_DIGEST = (
    "50d75a24a05a00736cb129a59fcfbdc81793a5c2084294cf29b5654a498b72f4"
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


RETAIN_PDF_ORIGINAL_CONTRACT_DIGEST = (
    "acc842a3cac79fff6118f9669915223f8c00f6c5e4e782b2fe34f136ee6a723c"
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


BIND_PDF_STAGE_RECIPE_CONTRACT_DIGEST = (
    "eac960d78055c4bab5061fa5819bceedb03e3bf9370c717db6d63549dca72249"
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


SEAL_PDF_BUILD_CONTRACT_DIGEST = "31fae4bbbf13dab1ee09da6873c76ae9c73972588c5a15ac40cb2522bd9c8070"


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
    product_key: ProductKey


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
    task_id: Column[TaskId]
    product_key: Column[ProductKey]
    logical_digest: Column[ContentDigest]
    release_id: Column[ReleaseId]
    source_digest: Column[str]
    schema_digest: Column[str]
    recipe_digest: Column[str]
    frozen_digest: Column[str]
    kind: Column[PdfPublishedRevisionKind]


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
            task_id=TaskId(row[1]),
            product_key=ProductKey(row[2]),
            logical_digest=ContentDigest(row[3]),
            release_id=ReleaseId(row[4]),
            source_digest=row[5],
            schema_digest=row[6],
            recipe_digest=row[7],
            frozen_digest=row[8],
            kind=cast(PdfPublishedRevisionKind, row[9]),
        )


def prepare_seal_pdf_build(
    *,
    build_id: str,
    task_id: TaskId,
    attempt: TaskAttempt,
    holder: str,
    frozen_digest: str,
    product_key: ProductKey,
    projection_context: PreparedRelease | None = None,
) -> Select[
    str, TaskId, ProductKey, ContentDigest, ReleaseId, str, str, str, str, PdfPublishedRevisionKind
]:
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
    return cast(
        Select[
            str,
            TaskId,
            ProductKey,
            ContentDigest,
            ReleaseId,
            str,
            str,
            str,
            str,
            PdfPublishedRevisionKind,
        ],
        _seal_pdf_build_statement.params(
            **{
                "build_id": _request.build_id,
                "task_id": _request.task_id,
                "attempt": _request.attempt,
                "holder": _request.holder,
                "frozen_digest": _request.frozen_digest,
                "product_key": _request.product_key,
            }
        ),
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
    product_key: ProductKey,
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


LOOKUP_PDF_VALIDATION_CONTRACT_DIGEST = (
    "a56d25587445e9eac8c06830a635baf67891b07f7793a5c3f16d13952612872e"
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
    "904490242999e72135fa80e34f6c2703270e926b29259b9ed735e3c2fe85edb2"
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


CHECK_PDF_BUILD_CONTRACT_DIGEST = "edff5c320e3a255ee9744f5ec6f3af8ec64f4d78d0e218f1313216b0bd073af0"


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
    "2075be4ea3fc2029ed154e1bb8b17fc75cd7c599d2bd26613d9815c75dce4885"
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
    "b9f0cb62c5d37d4752e84996f9cd9b57b864795b9626114a3fcbd0752d4fc491"
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
    "e4564135f3c9a4d96dfe1c8739ddf92d2cdebfc3a7a243ae52a7277ac716c1c0"
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


CALL_CONTRACT_DIGEST = "681e56e1ec251c6d249ae7f213d5b79589ff30ef0c60e7de972bb03ce30e4daa"
