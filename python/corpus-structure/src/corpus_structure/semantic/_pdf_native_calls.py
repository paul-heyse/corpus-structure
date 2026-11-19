"""Generated from authenticated fixed-call assets; do not edit."""

from __future__ import annotations

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
from corpus_structure.semantic.identifiers import RuntimeId as RuntimeId
from corpus_structure.semantic.identifiers import TaskAttempt as TaskAttempt
from corpus_structure.semantic.identifiers import TaskId as TaskId

from ._pdf_native_ids import (
    PdfBuildValidationCertificationBasis as PdfBuildValidationCertificationBasis,
)
from ._pdf_native_ids import (
    PdfCertificationRequirementCertificationBasis as PdfCertificationRequirementCertificationBasis,
)
from ._pdf_native_ids import PdfCertificationRequirementKind as PdfCertificationRequirementKind
from ._pdf_native_ids import PdfFrozenBuildKind as PdfFrozenBuildKind
from ._pdf_native_ids import (
    PdfProducerCertificationRecordKind as PdfProducerCertificationRecordKind,
)
from ._pdf_native_ids import PdfPublishedRevisionKind as PdfPublishedRevisionKind
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
    "9c5526a2ead5d3345b8d270d008482e81aaf8daec659aeda64fe6694e691ca2d"
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
    "f611e246b864a80a67e7e58b082246a3a3a997297ac0df74965538d162ef2c54"
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


ADOPT_PDF_BATCH_CONTRACT_DIGEST = "910e8e50eff8b0b14f075891a53643a12ff03850ba6b1673cfd99e54ddae090e"


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


ADOPT_PDF_COMPANIONS_CONTRACT_DIGEST = (
    "4bb29f292d3030062e46cf7a53cca4465037c7e22b1ef18590ace8c085198769"
)


class _adopt_pdf_companionsRequest(OperationResult):
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


_adopt_pdf_companions_function = func.ops.adopt_pdf_companions(
    bindparam("build_id", type_=Text()),
    bindparam("task_id", type_=BigInteger()),
    bindparam("attempt", type_=BigInteger()),
    bindparam("holder", type_=Text()),
    bindparam("replay_key", type_=Text()),
)
_adopt_pdf_companions_statement = select(_adopt_pdf_companions_function)


def prepare_adopt_pdf_companions(
    *,
    build_id: str,
    task_id: TaskId,
    attempt: TaskAttempt,
    holder: str,
    replay_key: str,
    projection_context: PreparedRelease | None = None,
) -> Select[None]:
    _request = _adopt_pdf_companionsRequest(
        build_id=build_id,
        task_id=task_id,
        attempt=attempt,
        holder=holder,
        replay_key=replay_key,
    )
    if projection_context is not None:
        require_call_context(
            projection_context,
            "adopt_pdf_companions",
            "adopt_pdf_companions",
            ADOPT_PDF_COMPANIONS_CONTRACT_DIGEST,
        )
    return _adopt_pdf_companions_statement.params(
        **{
            "build_id": _request.build_id,
            "task_id": _request.task_id,
            "attempt": _request.attempt,
            "holder": _request.holder,
            "replay_key": _request.replay_key,
        }
    )


def adopt_pdf_companions(
    conn: Connection,
    *,
    build_id: str,
    task_id: TaskId,
    attempt: TaskAttempt,
    holder: str,
    replay_key: str,
    projection_context: PreparedRelease | None = None,
) -> None:
    _statement = prepare_adopt_pdf_companions(
        build_id=build_id,
        task_id=task_id,
        attempt=attempt,
        holder=holder,
        replay_key=replay_key,
        projection_context=projection_context,
    )
    _native_result = conn.execute(_statement)
    with native_result_scope("adopt_pdf_companions", "adopt_pdf_companions"):
        _native_result.scalar_one()
    return None


BEGIN_PDF_BUILD_CONTRACT_DIGEST = "d7158a5cdd1b9affa4440e71960adb4394c6d52fa2776a2d310707c2f72a0ece"


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
    "ff1866dad47a81e138df99bd35f6d932c470bf1fe1a1dc69b12f51b4f8352044"
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
    "8198a22c48ee633f1e76c3f1f028cfe1b49d35f117b64027c56f7e709d17fa8c"
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
    "32f37cba1d8bd779d34a34183209380b40b7cc7e737d7affd69ac59569073727"
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
    "c6c9a14bb1b17fbfb5276d8fb8fd2de3dd68dd7b307bc877107d2a628fc4554a"
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
    "8e5d77b58e72576a2cec9d93902572bdb7238febc4193298fc350c2bc35c1a8d"
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
    "7facb9842c60228fa48dac466cabb43dc2b495044b234fc9d423eddf7207c21e"
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
    "9036571399319387b9726da1cdcf8f6eaf6abc6156e133c8a29697024b67572e"
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


PREPARE_PDF_COMPANIONS_CONTRACT_DIGEST = (
    "2e310e5dc2293ca754338079f169a74d4379d9d80b1f604ab12a901979d92d3d"
)


class _prepare_pdf_companionsRequest(OperationResult):
    pass


_prepare_pdf_companions_function = func.ops.prepare_pdf_companions()
_prepare_pdf_companions_statement = select(_prepare_pdf_companions_function)


def prepare_prepare_pdf_companions(
    *,
    projection_context: PreparedRelease | None = None,
) -> Select[None]:
    _request = _prepare_pdf_companionsRequest()
    if projection_context is not None:
        require_call_context(
            projection_context,
            "prepare_pdf_companions",
            "prepare_pdf_companions",
            PREPARE_PDF_COMPANIONS_CONTRACT_DIGEST,
        )
    return _prepare_pdf_companions_statement.params(**{})


def prepare_pdf_companions(
    conn: Connection,
    *,
    projection_context: PreparedRelease | None = None,
) -> None:
    _statement = prepare_prepare_pdf_companions(
        projection_context=projection_context,
    )
    _native_result = conn.execute(_statement)
    with native_result_scope("prepare_pdf_companions", "prepare_pdf_companions"):
        _native_result.scalar_one()
    return None


PROBE_PDF_SHARED_STREAMS_CONTRACT_DIGEST = (
    "192af57bca257b989e225bafd953edf3cfb89ddd6d0f3fc68cb1a9a9d2a3a86a"
)


class PdfSharedStreamStatus(NativeRowResult):
    stream_id: str
    verified: bool


class _probe_pdf_shared_streamsRequest(OperationResult):
    build_id: str
    task_id: Annotated[
        TaskId, Field(ge=TaskId(-9223372036854775808), le=TaskId(9223372036854775807))
    ]
    attempt: Annotated[
        TaskAttempt,
        Field(ge=TaskAttempt(-9223372036854775808), le=TaskAttempt(9223372036854775807)),
    ]
    holder: str
    streams: bytes


_probe_pdf_shared_streams_function = func.ops.probe_pdf_shared_streams(
    bindparam("build_id", type_=Text()),
    bindparam("task_id", type_=BigInteger()),
    bindparam("attempt", type_=BigInteger()),
    bindparam("holder", type_=Text()),
    bindparam("streams", type_=BYTEA()),
).table_valued(
    column("stream_id", Text()),
    column("verified", Boolean()),
)


class _probe_pdf_shared_streamsColumns(Protocol):
    stream_id: Column[str]
    verified: Column[bool]


_probe_pdf_shared_streams_columns = cast(
    _probe_pdf_shared_streamsColumns, _probe_pdf_shared_streams_function.c
)
_probe_pdf_shared_streams_statement = select(
    _probe_pdf_shared_streams_columns.stream_id,
    _probe_pdf_shared_streams_columns.verified,
).order_by(
    _probe_pdf_shared_streams_columns.stream_id.collate("C"),
)


def _probe_pdf_shared_streams_result(row: tuple[str, bool]) -> PdfSharedStreamStatus:
    with native_result_scope("probe_pdf_shared_streams", "PdfSharedStreamStatus"):
        return PdfSharedStreamStatus(
            stream_id=row[0],
            verified=row[1],
        )


def prepare_probe_pdf_shared_streams(
    *,
    build_id: str,
    task_id: TaskId,
    attempt: TaskAttempt,
    holder: str,
    streams: bytes,
    projection_context: PreparedRelease | None = None,
) -> Select[str, bool]:
    _request = _probe_pdf_shared_streamsRequest(
        build_id=build_id,
        task_id=task_id,
        attempt=attempt,
        holder=holder,
        streams=streams,
    )
    if projection_context is not None:
        require_call_context(
            projection_context,
            "probe_pdf_shared_streams",
            "probe_pdf_shared_streams",
            PROBE_PDF_SHARED_STREAMS_CONTRACT_DIGEST,
        )
    return _probe_pdf_shared_streams_statement.params(
        **{
            "build_id": _request.build_id,
            "task_id": _request.task_id,
            "attempt": _request.attempt,
            "holder": _request.holder,
            "streams": _request.streams,
        }
    )


materialize_probe_pdf_shared_streams = _probe_pdf_shared_streams_result


def probe_pdf_shared_streams(
    conn: Connection,
    *,
    build_id: str,
    task_id: TaskId,
    attempt: TaskAttempt,
    holder: str,
    streams: bytes,
    projection_context: PreparedRelease | None = None,
) -> tuple[PdfSharedStreamStatus, ...]:
    _statement = prepare_probe_pdf_shared_streams(
        build_id=build_id,
        task_id=task_id,
        attempt=attempt,
        holder=holder,
        streams=streams,
        projection_context=projection_context,
    )
    _native_result = conn.execute(_statement)
    with native_result_scope("probe_pdf_shared_streams", "PdfSharedStreamStatus"):
        return tuple(_probe_pdf_shared_streams_result(row) for row in _native_result)


PUBLISH_PDF_OBSERVATION_CONTRACT_DIGEST = (
    "223b5d8f7fd7f4d0c94fdf13b3c8aa938da39ce1ba7241af3dfed0bb2c39502c"
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
    runtime_id: RuntimeId
    contract_digest: str
    payload: bytes
    artifacts: tuple[bytes, ...]


_publish_pdf_observation_function = func.ops.publish_pdf_observation(
    bindparam("task_id", type_=BigInteger()),
    bindparam("attempt", type_=BigInteger()),
    bindparam("holder", type_=Text()),
    bindparam("runtime_id", type_=Text()),
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
    runtime_id: RuntimeId,
    contract_digest: str,
    payload: bytes,
    artifacts: tuple[bytes, ...],
    projection_context: PreparedRelease | None = None,
) -> Select[str]:
    _request = _publish_pdf_observationRequest(
        task_id=task_id,
        attempt=attempt,
        holder=holder,
        runtime_id=runtime_id,
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
            "runtime_id": _request.runtime_id,
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
    runtime_id: RuntimeId,
    contract_digest: str,
    payload: bytes,
    artifacts: tuple[bytes, ...],
    projection_context: PreparedRelease | None = None,
) -> str:
    _statement = prepare_publish_pdf_observation(
        task_id=task_id,
        attempt=attempt,
        holder=holder,
        runtime_id=runtime_id,
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
    "f35d91ffda72c04897a16c4d826085a12ab174731b7d796d4756d92cb9ac3e89"
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
    "92b9b8c2035fed2505274027ac17b2348a31664c4f0845af0829743a2a6e8dab"
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
    column("native_json", JSONB(astext_type=Text())),
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
    "c34ad6b126f78e506339e7a20d45a460af5ca105c78b5b93bd517bf88da46249"
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
    column("native_json", JSONB(astext_type=Text())),
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
    "4afb56263ad06ad222f86ce508c5b552f5d03d50d3c7b407421d83eb7d833e68"
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
    "be89032e572add06e2337a70ef835fe4a87a091f01e98e5c5a0870c3e5c335b7"
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
    column("body", JSONB(astext_type=Text())),
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
    "5d7277f49e9550f7c5a2ae01374403dc3711766ae5e8b87dab9c90f9acca7c25"
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
    "31b94a577b52ac83ca1ff0002aa620f6e7d1e1ad16030f38fde71a71a8297664"
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
    "394f05085a7cd194b3a44e0b5d62d31ba42c40319934b6c620cad5919f4ac0ab"
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
    "73c6e10f80a0f7cc2a4a38c48a5f1668f81292fdc2254d8e2742cd4b026d74cc"
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
    "946525868a55e437946380ce99723ca238b0a2b08ca3f2b6ff7e9691488d03c6"
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
    bindparam("filters", type_=JSONB(astext_type=Text())),
    bindparam("after", type_=JSONB(none_as_null=True)),
    bindparam("limit", type_=Integer()),
    type_=JSONB(astext_type=Text()),
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
    "95bfd5a6f28480cc3ca7414be1bcf3584700f8ea9fa6fcff750139a305927e17"
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
    type_=JSONB(astext_type=Text()),
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
    "f55cd761179f84d9b9458b3b95444f54de1667d2cdf77e9fb99dac95be3023ce"
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
    type_=JSONB(astext_type=Text()),
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
    "df0738df0eacc5c406cac32aeafe4a5578abed735c67a01d95c9f1dc585a0ec9"
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
    type_=JSONB(astext_type=Text()),
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
    "e5407804939cc59efa011ad7de90bc59eab7aa95cfefcb9554bb491962e171dd"
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
    type_=JSONB(astext_type=Text()),
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
    "64bed282305d990bc38e6dfdff81df2462803edc8db05a00c8d2b67c15136788"
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
    type_=JSONB(astext_type=Text()),
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
    "5c9b98e6d94c094f749eab39112e155dea27e3450fef8dfe1e835e36d9f2add1"
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
    "1d2dd2a825e21f16d0941633fb0908a09dadbbfde2537dfdabd9ed1fb29e900b"
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
    "39c994edb32338f4a8cb8c00561b693840842bb109096a0144a1a8888e0af3e4"
)


class PdfBuildValidation(NativeRowResult):
    build_id: str
    frozen_digest: str
    logical_digest: str
    contract_digest: str
    native_callbacks: bool
    native_contract_digest: str
    certification_basis: PdfBuildValidationCertificationBasis
    lowering_identity: str
    attested_logical_digest: str
    native_document_digest: str
    oracle_receipt_id: str


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
    column("certification_basis", Text()),
    column("lowering_identity", Text()),
    column("attested_logical_digest", Text()),
    column("native_document_digest", Text()),
    column("oracle_receipt_id", Text()),
)


class _read_pdf_published_validationColumns(Protocol):
    build_id: Column[str]
    frozen_digest: Column[str]
    logical_digest: Column[str]
    contract_digest: Column[str]
    native_callbacks: Column[bool]
    native_contract_digest: Column[str]
    certification_basis: Column[PdfBuildValidationCertificationBasis]
    lowering_identity: Column[str]
    attested_logical_digest: Column[str]
    native_document_digest: Column[str]
    oracle_receipt_id: Column[str]


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
    _read_pdf_published_validation_columns.certification_basis,
    _read_pdf_published_validation_columns.lowering_identity,
    _read_pdf_published_validation_columns.attested_logical_digest,
    _read_pdf_published_validation_columns.native_document_digest,
    _read_pdf_published_validation_columns.oracle_receipt_id,
)


def _read_pdf_published_validation_result(
    row: tuple[str, str, str, str, bool, str, str, str, str, str, str],
) -> PdfBuildValidation:
    with native_result_scope("read_pdf_product", "PdfBuildValidation"):
        return PdfBuildValidation(
            build_id=row[0],
            frozen_digest=row[1],
            logical_digest=row[2],
            contract_digest=row[3],
            native_callbacks=row[4],
            native_contract_digest=row[5],
            certification_basis=cast(PdfBuildValidationCertificationBasis, row[6]),
            lowering_identity=row[7],
            attested_logical_digest=row[8],
            native_document_digest=row[9],
            oracle_receipt_id=row[10],
        )


def prepare_read_pdf_published_validation(
    *,
    task_id: TaskId,
    product_key: ProductKey,
    content_digest: ContentDigest,
    projection_context: PreparedRelease | None = None,
) -> Select[
    str, str, str, str, bool, str, PdfBuildValidationCertificationBasis, str, str, str, str
]:
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
    return cast(
        Select[
            str, str, str, str, bool, str, PdfBuildValidationCertificationBasis, str, str, str, str
        ],
        _read_pdf_published_validation_statement.params(
            **{
                "task_id": _request.task_id,
                "product_key": _request.product_key,
                "content_digest": _request.content_digest,
            }
        ),
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
    "37fc9884f33189418fcb3dd5b7c1dbe3607e98cf427e53d60fce283dbe7abf8b"
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


REGISTER_PDF_SPOOL_PRODUCER_CONTRACT_DIGEST = (
    "5df2f4378b75ea9d6b1f3086559b5b2f1b2a180ee98521090c48e05d4864b10c"
)


class _register_pdf_spool_producerRequest(OperationResult):
    build_id: str
    task_id: Annotated[
        TaskId, Field(ge=TaskId(-9223372036854775808), le=TaskId(9223372036854775807))
    ]
    attempt: Annotated[
        TaskAttempt,
        Field(ge=TaskAttempt(-9223372036854775808), le=TaskAttempt(9223372036854775807)),
    ]
    holder: str
    runtime_id: RuntimeId
    writer_device: Annotated[int, Field(ge=-9223372036854775808, le=9223372036854775807)]
    writer_inode: Annotated[int, Field(ge=-9223372036854775808, le=9223372036854775807)]
    premises_bytes: bytes


_register_pdf_spool_producer_function = func.ops.register_pdf_spool_producer(
    bindparam("build_id", type_=Text()),
    bindparam("task_id", type_=BigInteger()),
    bindparam("attempt", type_=BigInteger()),
    bindparam("holder", type_=Text()),
    bindparam("runtime_id", type_=Text()),
    bindparam("writer_device", type_=BigInteger()),
    bindparam("writer_inode", type_=BigInteger()),
    bindparam("premises_bytes", type_=BYTEA()),
    type_=Text(),
)
_register_pdf_spool_producer_statement = select(_register_pdf_spool_producer_function)


def prepare_register_pdf_spool_producer(
    *,
    build_id: str,
    task_id: TaskId,
    attempt: TaskAttempt,
    holder: str,
    runtime_id: RuntimeId,
    writer_device: int,
    writer_inode: int,
    premises_bytes: bytes,
    projection_context: PreparedRelease | None = None,
) -> Select[str]:
    _request = _register_pdf_spool_producerRequest(
        build_id=build_id,
        task_id=task_id,
        attempt=attempt,
        holder=holder,
        runtime_id=runtime_id,
        writer_device=writer_device,
        writer_inode=writer_inode,
        premises_bytes=premises_bytes,
    )
    if projection_context is not None:
        require_call_context(
            projection_context,
            "retain_pdf_original",
            "register_pdf_spool_producer",
            REGISTER_PDF_SPOOL_PRODUCER_CONTRACT_DIGEST,
        )
    return _register_pdf_spool_producer_statement.params(
        **{
            "build_id": _request.build_id,
            "task_id": _request.task_id,
            "attempt": _request.attempt,
            "holder": _request.holder,
            "runtime_id": _request.runtime_id,
            "writer_device": _request.writer_device,
            "writer_inode": _request.writer_inode,
            "premises_bytes": _request.premises_bytes,
        }
    )


_register_pdf_spool_producer_adapter = TypeAdapter(str)


def materialize_register_pdf_spool_producer(row: tuple[str]) -> str:
    with native_result_scope("retain_pdf_original", "register_pdf_spool_producer", "identity"):
        checked = _register_pdf_spool_producer_adapter.validate_python(row[0], strict=True)
        return checked


def register_pdf_spool_producer(
    conn: Connection,
    *,
    build_id: str,
    task_id: TaskId,
    attempt: TaskAttempt,
    holder: str,
    runtime_id: RuntimeId,
    writer_device: int,
    writer_inode: int,
    premises_bytes: bytes,
    projection_context: PreparedRelease | None = None,
) -> str:
    _statement = prepare_register_pdf_spool_producer(
        build_id=build_id,
        task_id=task_id,
        attempt=attempt,
        holder=holder,
        runtime_id=runtime_id,
        writer_device=writer_device,
        writer_inode=writer_inode,
        premises_bytes=premises_bytes,
        projection_context=projection_context,
    )
    _native_result = conn.execute(_statement)
    with native_result_scope("retain_pdf_original", "register_pdf_spool_producer"):
        row = _native_result.one()
        return materialize_register_pdf_spool_producer(row)


REGISTER_PDF_SPOOL_CONTRIBUTOR_CONTRACT_DIGEST = (
    "bc88f401d15f96c324c42f1f4568054992d5a3d0358b1952be2154c1c6c7feea"
)


class _register_pdf_spool_contributorRequest(OperationResult):
    build_id: str
    task_id: Annotated[
        TaskId, Field(ge=TaskId(-9223372036854775808), le=TaskId(9223372036854775807))
    ]
    attempt: Annotated[
        TaskAttempt,
        Field(ge=TaskAttempt(-9223372036854775808), le=TaskAttempt(9223372036854775807)),
    ]
    holder: str
    runtime_id: RuntimeId
    producer_id: str
    manifest_bytes: bytes
    selected_replays: bytes


_register_pdf_spool_contributor_function = func.ops.register_pdf_spool_contributor(
    bindparam("build_id", type_=Text()),
    bindparam("task_id", type_=BigInteger()),
    bindparam("attempt", type_=BigInteger()),
    bindparam("holder", type_=Text()),
    bindparam("runtime_id", type_=Text()),
    bindparam("producer_id", type_=Text()),
    bindparam("manifest_bytes", type_=BYTEA()),
    bindparam("selected_replays", type_=BYTEA()),
    type_=Text(),
)
_register_pdf_spool_contributor_statement = select(_register_pdf_spool_contributor_function)


def prepare_register_pdf_spool_contributor(
    *,
    build_id: str,
    task_id: TaskId,
    attempt: TaskAttempt,
    holder: str,
    runtime_id: RuntimeId,
    producer_id: str,
    manifest_bytes: bytes,
    selected_replays: bytes,
    projection_context: PreparedRelease | None = None,
) -> Select[str]:
    _request = _register_pdf_spool_contributorRequest(
        build_id=build_id,
        task_id=task_id,
        attempt=attempt,
        holder=holder,
        runtime_id=runtime_id,
        producer_id=producer_id,
        manifest_bytes=manifest_bytes,
        selected_replays=selected_replays,
    )
    if projection_context is not None:
        require_call_context(
            projection_context,
            "retain_pdf_original",
            "register_pdf_spool_contributor",
            REGISTER_PDF_SPOOL_CONTRIBUTOR_CONTRACT_DIGEST,
        )
    return _register_pdf_spool_contributor_statement.params(
        **{
            "build_id": _request.build_id,
            "task_id": _request.task_id,
            "attempt": _request.attempt,
            "holder": _request.holder,
            "runtime_id": _request.runtime_id,
            "producer_id": _request.producer_id,
            "manifest_bytes": _request.manifest_bytes,
            "selected_replays": _request.selected_replays,
        }
    )


_register_pdf_spool_contributor_adapter = TypeAdapter(str)


def materialize_register_pdf_spool_contributor(row: tuple[str]) -> str:
    with native_result_scope("retain_pdf_original", "register_pdf_spool_contributor", "identity"):
        checked = _register_pdf_spool_contributor_adapter.validate_python(row[0], strict=True)
        return checked


def register_pdf_spool_contributor(
    conn: Connection,
    *,
    build_id: str,
    task_id: TaskId,
    attempt: TaskAttempt,
    holder: str,
    runtime_id: RuntimeId,
    producer_id: str,
    manifest_bytes: bytes,
    selected_replays: bytes,
    projection_context: PreparedRelease | None = None,
) -> str:
    _statement = prepare_register_pdf_spool_contributor(
        build_id=build_id,
        task_id=task_id,
        attempt=attempt,
        holder=holder,
        runtime_id=runtime_id,
        producer_id=producer_id,
        manifest_bytes=manifest_bytes,
        selected_replays=selected_replays,
        projection_context=projection_context,
    )
    _native_result = conn.execute(_statement)
    with native_result_scope("retain_pdf_original", "register_pdf_spool_contributor"):
        row = _native_result.one()
        return materialize_register_pdf_spool_contributor(row)


READ_PDF_SPOOL_RECOVERY_CANDIDATES_CONTRACT_DIGEST = (
    "92e6970f8c24ce006d1a10e6e6492a811c019b5a857a7f34deb9adb8251f611a"
)


class PdfSpoolRecoveryCandidate(NativeRowResult):
    build_id: str
    task_id: int
    producer_id: str
    attempt: int
    holder: str
    writer_device: int
    writer_inode: int
    premises_bytes: bytes


class _read_pdf_spool_recovery_candidatesRequest(OperationResult):
    build_id: str
    task_id: Annotated[
        TaskId, Field(ge=TaskId(-9223372036854775808), le=TaskId(9223372036854775807))
    ]
    attempt: Annotated[
        TaskAttempt,
        Field(ge=TaskAttempt(-9223372036854775808), le=TaskAttempt(9223372036854775807)),
    ]
    holder: str
    runtime_id: RuntimeId
    premises_bytes: bytes


_read_pdf_spool_recovery_candidates_function = func.ops.read_pdf_spool_recovery_candidates(
    bindparam("build_id", type_=Text()),
    bindparam("task_id", type_=BigInteger()),
    bindparam("attempt", type_=BigInteger()),
    bindparam("holder", type_=Text()),
    bindparam("runtime_id", type_=Text()),
    bindparam("premises_bytes", type_=BYTEA()),
).table_valued(
    column("build_id", Text()),
    column("task_id", BigInteger()),
    column("producer_id", Text()),
    column("attempt", BigInteger()),
    column("holder", Text()),
    column("writer_device", BigInteger()),
    column("writer_inode", BigInteger()),
    column("premises_bytes", BYTEA()),
)


class _read_pdf_spool_recovery_candidatesColumns(Protocol):
    build_id: Column[str]
    task_id: Column[int]
    producer_id: Column[str]
    attempt: Column[int]
    holder: Column[str]
    writer_device: Column[int]
    writer_inode: Column[int]
    premises_bytes: Column[bytes]


_read_pdf_spool_recovery_candidates_columns = cast(
    _read_pdf_spool_recovery_candidatesColumns, _read_pdf_spool_recovery_candidates_function.c
)
_read_pdf_spool_recovery_candidates_statement = select(
    _read_pdf_spool_recovery_candidates_columns.build_id,
    _read_pdf_spool_recovery_candidates_columns.task_id,
    _read_pdf_spool_recovery_candidates_columns.producer_id,
    _read_pdf_spool_recovery_candidates_columns.attempt,
    _read_pdf_spool_recovery_candidates_columns.holder,
    _read_pdf_spool_recovery_candidates_columns.writer_device,
    _read_pdf_spool_recovery_candidates_columns.writer_inode,
    _read_pdf_spool_recovery_candidates_columns.premises_bytes,
)


def _read_pdf_spool_recovery_candidates_result(
    row: tuple[str, int, str, int, str, int, int, bytes],
) -> PdfSpoolRecoveryCandidate:
    with native_result_scope("retain_pdf_original", "PdfSpoolRecoveryCandidate"):
        return PdfSpoolRecoveryCandidate(
            build_id=row[0],
            task_id=row[1],
            producer_id=row[2],
            attempt=row[3],
            holder=row[4],
            writer_device=row[5],
            writer_inode=row[6],
            premises_bytes=row[7],
        )


def prepare_read_pdf_spool_recovery_candidates(
    *,
    build_id: str,
    task_id: TaskId,
    attempt: TaskAttempt,
    holder: str,
    runtime_id: RuntimeId,
    premises_bytes: bytes,
    projection_context: PreparedRelease | None = None,
) -> Select[str, int, str, int, str, int, int, bytes]:
    _request = _read_pdf_spool_recovery_candidatesRequest(
        build_id=build_id,
        task_id=task_id,
        attempt=attempt,
        holder=holder,
        runtime_id=runtime_id,
        premises_bytes=premises_bytes,
    )
    if projection_context is not None:
        require_call_context(
            projection_context,
            "retain_pdf_original",
            "read_pdf_spool_recovery_candidates",
            READ_PDF_SPOOL_RECOVERY_CANDIDATES_CONTRACT_DIGEST,
        )
    return _read_pdf_spool_recovery_candidates_statement.params(
        **{
            "build_id": _request.build_id,
            "task_id": _request.task_id,
            "attempt": _request.attempt,
            "holder": _request.holder,
            "runtime_id": _request.runtime_id,
            "premises_bytes": _request.premises_bytes,
        }
    )


materialize_read_pdf_spool_recovery_candidates = _read_pdf_spool_recovery_candidates_result


def read_pdf_spool_recovery_candidates(
    conn: Connection,
    *,
    build_id: str,
    task_id: TaskId,
    attempt: TaskAttempt,
    holder: str,
    runtime_id: RuntimeId,
    premises_bytes: bytes,
    projection_context: PreparedRelease | None = None,
) -> tuple[PdfSpoolRecoveryCandidate, ...]:
    _statement = prepare_read_pdf_spool_recovery_candidates(
        build_id=build_id,
        task_id=task_id,
        attempt=attempt,
        holder=holder,
        runtime_id=runtime_id,
        premises_bytes=premises_bytes,
        projection_context=projection_context,
    )
    _native_result = conn.execute(_statement)
    with native_result_scope("retain_pdf_original", "PdfSpoolRecoveryCandidate"):
        return tuple(_read_pdf_spool_recovery_candidates_result(row) for row in _native_result)


READ_PDF_SPOOL_CONTRIBUTORS_CONTRACT_DIGEST = (
    "ca4df249ef2fbfde28e65ee5f9c23436259cc96348d2136d2f35d3a54c2dbef1"
)


class PdfSpoolContributorReceipt(NativeRowResult):
    producer_id: str
    task_id: int
    producer_attempt: int
    producer_holder: str
    runtime_id: str
    runtime_manifest_digest: str
    manifest_digest: str
    selection_digest: str
    adopter_attempt: int
    adopter_holder: str


class _read_pdf_spool_contributorsRequest(OperationResult):
    build_id: str
    task_id: Annotated[
        TaskId, Field(ge=TaskId(-9223372036854775808), le=TaskId(9223372036854775807))
    ]
    attempt: Annotated[
        TaskAttempt,
        Field(ge=TaskAttempt(-9223372036854775808), le=TaskAttempt(9223372036854775807)),
    ]
    holder: str


_read_pdf_spool_contributors_function = func.ops.read_pdf_spool_contributors(
    bindparam("build_id", type_=Text()),
    bindparam("task_id", type_=BigInteger()),
    bindparam("attempt", type_=BigInteger()),
    bindparam("holder", type_=Text()),
).table_valued(
    column("producer_id", Text()),
    column("task_id", BigInteger()),
    column("producer_attempt", BigInteger()),
    column("producer_holder", Text()),
    column("runtime_id", Text()),
    column("runtime_manifest_digest", Text()),
    column("manifest_digest", Text()),
    column("selection_digest", Text()),
    column("adopter_attempt", BigInteger()),
    column("adopter_holder", Text()),
)


class _read_pdf_spool_contributorsColumns(Protocol):
    producer_id: Column[str]
    task_id: Column[int]
    producer_attempt: Column[int]
    producer_holder: Column[str]
    runtime_id: Column[str]
    runtime_manifest_digest: Column[str]
    manifest_digest: Column[str]
    selection_digest: Column[str]
    adopter_attempt: Column[int]
    adopter_holder: Column[str]


_read_pdf_spool_contributors_columns = cast(
    _read_pdf_spool_contributorsColumns, _read_pdf_spool_contributors_function.c
)
_read_pdf_spool_contributors_statement = select(
    _read_pdf_spool_contributors_columns.producer_id,
    _read_pdf_spool_contributors_columns.task_id,
    _read_pdf_spool_contributors_columns.producer_attempt,
    _read_pdf_spool_contributors_columns.producer_holder,
    _read_pdf_spool_contributors_columns.runtime_id,
    _read_pdf_spool_contributors_columns.runtime_manifest_digest,
    _read_pdf_spool_contributors_columns.manifest_digest,
    _read_pdf_spool_contributors_columns.selection_digest,
    _read_pdf_spool_contributors_columns.adopter_attempt,
    _read_pdf_spool_contributors_columns.adopter_holder,
).order_by(
    _read_pdf_spool_contributors_columns.producer_id.collate("C"),
    _read_pdf_spool_contributors_columns.manifest_digest.collate("C"),
    _read_pdf_spool_contributors_columns.selection_digest.collate("C"),
)


def _read_pdf_spool_contributors_result(
    row: tuple[str, int, int, str, str, str, str, str, int, str],
) -> PdfSpoolContributorReceipt:
    with native_result_scope("retain_pdf_original", "PdfSpoolContributorReceipt"):
        return PdfSpoolContributorReceipt(
            producer_id=row[0],
            task_id=row[1],
            producer_attempt=row[2],
            producer_holder=row[3],
            runtime_id=row[4],
            runtime_manifest_digest=row[5],
            manifest_digest=row[6],
            selection_digest=row[7],
            adopter_attempt=row[8],
            adopter_holder=row[9],
        )


def prepare_read_pdf_spool_contributors(
    *,
    build_id: str,
    task_id: TaskId,
    attempt: TaskAttempt,
    holder: str,
    projection_context: PreparedRelease | None = None,
) -> Select[str, int, int, str, str, str, str, str, int, str]:
    _request = _read_pdf_spool_contributorsRequest(
        build_id=build_id,
        task_id=task_id,
        attempt=attempt,
        holder=holder,
    )
    if projection_context is not None:
        require_call_context(
            projection_context,
            "retain_pdf_original",
            "read_pdf_spool_contributors",
            READ_PDF_SPOOL_CONTRIBUTORS_CONTRACT_DIGEST,
        )
    return cast(
        Select[str, int, int, str, str, str, str, str, int, str],
        _read_pdf_spool_contributors_statement.params(
            **{
                "build_id": _request.build_id,
                "task_id": _request.task_id,
                "attempt": _request.attempt,
                "holder": _request.holder,
            }
        ),
    )


materialize_read_pdf_spool_contributors = _read_pdf_spool_contributors_result


def read_pdf_spool_contributors(
    conn: Connection,
    *,
    build_id: str,
    task_id: TaskId,
    attempt: TaskAttempt,
    holder: str,
    projection_context: PreparedRelease | None = None,
) -> tuple[PdfSpoolContributorReceipt, ...]:
    _statement = prepare_read_pdf_spool_contributors(
        build_id=build_id,
        task_id=task_id,
        attempt=attempt,
        holder=holder,
        projection_context=projection_context,
    )
    _native_result = conn.execute(_statement)
    with native_result_scope("retain_pdf_original", "PdfSpoolContributorReceipt"):
        return tuple(_read_pdf_spool_contributors_result(row) for row in _native_result)


READ_PDF_PRODUCER_BASIS_CONTRACT_DIGEST = (
    "50f278989ed5ef70af527ab36e0457e0aae5cb81059ab893649ad971f453c4a8"
)


class PdfSpoolProducerBasis(NativeRowResult):
    request_id: str
    generation: int
    release_id: str
    operation: str
    definition: str
    recipe: str
    implementation: str
    execution_profile: str
    runtime_id: str
    runtime_manifest_digest: str
    pdf_domain_digest: str


class _read_pdf_producer_basisRequest(OperationResult):
    task_id: Annotated[
        TaskId, Field(ge=TaskId(-9223372036854775808), le=TaskId(9223372036854775807))
    ]
    attempt: Annotated[
        TaskAttempt,
        Field(ge=TaskAttempt(-9223372036854775808), le=TaskAttempt(9223372036854775807)),
    ]
    holder: str
    runtime_id: RuntimeId


_read_pdf_producer_basis_function = func.ops.read_pdf_producer_basis(
    bindparam("task_id", type_=BigInteger()),
    bindparam("attempt", type_=BigInteger()),
    bindparam("holder", type_=Text()),
    bindparam("runtime_id", type_=Text()),
).table_valued(
    column("request_id", Text()),
    column("generation", BigInteger()),
    column("release_id", Text()),
    column("operation", Text()),
    column("definition", Text()),
    column("recipe", Text()),
    column("implementation", Text()),
    column("execution_profile", Text()),
    column("runtime_id", Text()),
    column("runtime_manifest_digest", Text()),
    column("pdf_domain_digest", Text()),
)


class _read_pdf_producer_basisColumns(Protocol):
    request_id: Column[str]
    generation: Column[int]
    release_id: Column[str]
    operation: Column[str]
    definition: Column[str]
    recipe: Column[str]
    implementation: Column[str]
    execution_profile: Column[str]
    runtime_id: Column[str]
    runtime_manifest_digest: Column[str]
    pdf_domain_digest: Column[str]


_read_pdf_producer_basis_columns = cast(
    _read_pdf_producer_basisColumns, _read_pdf_producer_basis_function.c
)
_read_pdf_producer_basis_statement = select(
    _read_pdf_producer_basis_columns.request_id,
    _read_pdf_producer_basis_columns.generation,
    _read_pdf_producer_basis_columns.release_id,
    _read_pdf_producer_basis_columns.operation,
    _read_pdf_producer_basis_columns.definition,
    _read_pdf_producer_basis_columns.recipe,
    _read_pdf_producer_basis_columns.implementation,
    _read_pdf_producer_basis_columns.execution_profile,
    _read_pdf_producer_basis_columns.runtime_id,
    _read_pdf_producer_basis_columns.runtime_manifest_digest,
    _read_pdf_producer_basis_columns.pdf_domain_digest,
)


def _read_pdf_producer_basis_result(
    row: tuple[str, int, str, str, str, str, str, str, str, str, str],
) -> PdfSpoolProducerBasis:
    with native_result_scope("retain_pdf_original", "PdfSpoolProducerBasis"):
        return PdfSpoolProducerBasis(
            request_id=row[0],
            generation=row[1],
            release_id=row[2],
            operation=row[3],
            definition=row[4],
            recipe=row[5],
            implementation=row[6],
            execution_profile=row[7],
            runtime_id=row[8],
            runtime_manifest_digest=row[9],
            pdf_domain_digest=row[10],
        )


def prepare_read_pdf_producer_basis(
    *,
    task_id: TaskId,
    attempt: TaskAttempt,
    holder: str,
    runtime_id: RuntimeId,
    projection_context: PreparedRelease | None = None,
) -> Select[str, int, str, str, str, str, str, str, str, str, str]:
    _request = _read_pdf_producer_basisRequest(
        task_id=task_id,
        attempt=attempt,
        holder=holder,
        runtime_id=runtime_id,
    )
    if projection_context is not None:
        require_call_context(
            projection_context,
            "retain_pdf_original",
            "read_pdf_producer_basis",
            READ_PDF_PRODUCER_BASIS_CONTRACT_DIGEST,
        )
    return cast(
        Select[str, int, str, str, str, str, str, str, str, str, str],
        _read_pdf_producer_basis_statement.params(
            **{
                "task_id": _request.task_id,
                "attempt": _request.attempt,
                "holder": _request.holder,
                "runtime_id": _request.runtime_id,
            }
        ),
    )


materialize_read_pdf_producer_basis = _read_pdf_producer_basis_result


def read_pdf_producer_basis(
    conn: Connection,
    *,
    task_id: TaskId,
    attempt: TaskAttempt,
    holder: str,
    runtime_id: RuntimeId,
    projection_context: PreparedRelease | None = None,
) -> PdfSpoolProducerBasis:
    _statement = prepare_read_pdf_producer_basis(
        task_id=task_id,
        attempt=attempt,
        holder=holder,
        runtime_id=runtime_id,
        projection_context=projection_context,
    )
    _native_result = conn.execute(_statement)
    with native_result_scope("retain_pdf_original", "PdfSpoolProducerBasis"):
        return _read_pdf_producer_basis_result(_native_result.one())


RETAIN_PDF_ORIGINAL_CONTRACT_DIGEST = (
    "b5451f5b6704f12b36b11071c62fcedb5ed458415da54d7acae71268800426e1"
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
    "40bddc45b64a438e6cae9926ced0f52d82d1c1fcfee1a014eacdef1f7afd2fb2"
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


SEAL_PDF_BUILD_CONTRACT_DIGEST = "6e9945c524e9547785013a90c5240268c0a44883c09a25558d7c4fc1ccee6379"


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


RECORD_PDF_PRODUCER_CERTIFICATION_CONTRACT_DIGEST = (
    "6ffaed1daea24911ac871ecced506217e1cbf815299630a13ea2f607f8c9f600"
)


class _record_pdf_producer_certificationRequest(OperationResult):
    build_id: str
    task_id: Annotated[
        TaskId, Field(ge=TaskId(-9223372036854775808), le=TaskId(9223372036854775807))
    ]
    attempt: Annotated[
        TaskAttempt,
        Field(ge=TaskAttempt(-9223372036854775808), le=TaskAttempt(9223372036854775807)),
    ]
    holder: str
    lowering_identity: str
    kind: PdfProducerCertificationRecordKind
    logical_digest: str
    native_document_digest: str
    stream_inventory_digest: str


_record_pdf_producer_certification_function = func.ops.record_pdf_producer_certification(
    bindparam("build_id", type_=Text()),
    bindparam("task_id", type_=BigInteger()),
    bindparam("attempt", type_=BigInteger()),
    bindparam("holder", type_=Text()),
    bindparam("lowering_identity", type_=Text()),
    bindparam("kind", type_=Text()),
    bindparam("logical_digest", type_=Text()),
    bindparam("native_document_digest", type_=Text()),
    bindparam("stream_inventory_digest", type_=Text()),
)
_record_pdf_producer_certification_statement = select(_record_pdf_producer_certification_function)


def prepare_record_pdf_producer_certification(
    *,
    build_id: str,
    task_id: TaskId,
    attempt: TaskAttempt,
    holder: str,
    lowering_identity: str,
    kind: PdfProducerCertificationRecordKind,
    logical_digest: str,
    native_document_digest: str,
    stream_inventory_digest: str,
    projection_context: PreparedRelease | None = None,
) -> Select[None]:
    _request = _record_pdf_producer_certificationRequest(
        build_id=build_id,
        task_id=task_id,
        attempt=attempt,
        holder=holder,
        lowering_identity=lowering_identity,
        kind=kind,
        logical_digest=logical_digest,
        native_document_digest=native_document_digest,
        stream_inventory_digest=stream_inventory_digest,
    )
    if projection_context is not None:
        require_call_context(
            projection_context,
            "validate_pdf_build",
            "record_pdf_producer_certification",
            RECORD_PDF_PRODUCER_CERTIFICATION_CONTRACT_DIGEST,
        )
    return _record_pdf_producer_certification_statement.params(
        **{
            "build_id": _request.build_id,
            "task_id": _request.task_id,
            "attempt": _request.attempt,
            "holder": _request.holder,
            "lowering_identity": _request.lowering_identity,
            "kind": _request.kind,
            "logical_digest": _request.logical_digest,
            "native_document_digest": _request.native_document_digest,
            "stream_inventory_digest": _request.stream_inventory_digest,
        }
    )


def record_pdf_producer_certification(
    conn: Connection,
    *,
    build_id: str,
    task_id: TaskId,
    attempt: TaskAttempt,
    holder: str,
    lowering_identity: str,
    kind: PdfProducerCertificationRecordKind,
    logical_digest: str,
    native_document_digest: str,
    stream_inventory_digest: str,
    projection_context: PreparedRelease | None = None,
) -> None:
    _statement = prepare_record_pdf_producer_certification(
        build_id=build_id,
        task_id=task_id,
        attempt=attempt,
        holder=holder,
        lowering_identity=lowering_identity,
        kind=kind,
        logical_digest=logical_digest,
        native_document_digest=native_document_digest,
        stream_inventory_digest=stream_inventory_digest,
        projection_context=projection_context,
    )
    _native_result = conn.execute(_statement)
    with native_result_scope("validate_pdf_build", "record_pdf_producer_certification"):
        _native_result.scalar_one()
    return None


STAGE_PDF_ACCESS_BATCH_CONTRACT_DIGEST = (
    "1cb728135ac27c26674348c89695f4c23594ca836a59e575a76d95bc5931535d"
)


class _stage_pdf_access_batchRequest(OperationResult):
    build_id: str
    task_id: Annotated[
        TaskId, Field(ge=TaskId(-9223372036854775808), le=TaskId(9223372036854775807))
    ]
    attempt: Annotated[
        TaskAttempt,
        Field(ge=TaskAttempt(-9223372036854775808), le=TaskAttempt(9223372036854775807)),
    ]
    holder: str
    rows: JsonValue


_stage_pdf_access_batch_function = func.ops.stage_pdf_access_batch(
    bindparam("build_id", type_=Text()),
    bindparam("task_id", type_=BigInteger()),
    bindparam("attempt", type_=BigInteger()),
    bindparam("holder", type_=Text()),
    bindparam("rows", type_=JSONB(astext_type=Text())),
)
_stage_pdf_access_batch_statement = select(_stage_pdf_access_batch_function)


def prepare_stage_pdf_access_batch(
    *,
    build_id: str,
    task_id: TaskId,
    attempt: TaskAttempt,
    holder: str,
    rows: JsonValue,
    projection_context: PreparedRelease | None = None,
) -> Select[None]:
    _request = _stage_pdf_access_batchRequest(
        build_id=build_id,
        task_id=task_id,
        attempt=attempt,
        holder=holder,
        rows=rows,
    )
    if projection_context is not None:
        require_call_context(
            projection_context,
            "validate_pdf_build",
            "stage_pdf_access_batch",
            STAGE_PDF_ACCESS_BATCH_CONTRACT_DIGEST,
        )
    return _stage_pdf_access_batch_statement.params(
        **{
            "build_id": _request.build_id,
            "task_id": _request.task_id,
            "attempt": _request.attempt,
            "holder": _request.holder,
            "rows": _request.rows,
        }
    )


def stage_pdf_access_batch(
    conn: Connection,
    *,
    build_id: str,
    task_id: TaskId,
    attempt: TaskAttempt,
    holder: str,
    rows: JsonValue,
    projection_context: PreparedRelease | None = None,
) -> None:
    _statement = prepare_stage_pdf_access_batch(
        build_id=build_id,
        task_id=task_id,
        attempt=attempt,
        holder=holder,
        rows=rows,
        projection_context=projection_context,
    )
    _native_result = conn.execute(_statement)
    with native_result_scope("validate_pdf_build", "stage_pdf_access_batch"):
        _native_result.scalar_one()
    return None


READ_PDF_CERTIFICATION_REQUIREMENT_CONTRACT_DIGEST = (
    "ba74ada8d46dce168a656d5379cff45cfdc1afbbdcd84ea9128d99c6d18e3d8e"
)


class PdfCertificationRequirement(NativeRowResult):
    lowering_identity: str
    kind: PdfCertificationRequirementKind
    logical_digest: str
    native_document_digest: str
    oracle_receipt_id: str | None
    certification_basis: PdfCertificationRequirementCertificationBasis


class _read_pdf_certification_requirementRequest(OperationResult):
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


_read_pdf_certification_requirement_function = func.ops.read_pdf_certification_requirement(
    bindparam("build_id", type_=Text()),
    bindparam("task_id", type_=BigInteger()),
    bindparam("attempt", type_=BigInteger()),
    bindparam("holder", type_=Text()),
    bindparam("frozen_digest", type_=Text()),
).table_valued(
    column("lowering_identity", Text()),
    column("kind", Text()),
    column("logical_digest", Text()),
    column("native_document_digest", Text()),
    column("oracle_receipt_id", Text()),
    column("certification_basis", Text()),
)


class _read_pdf_certification_requirementColumns(Protocol):
    lowering_identity: Column[str]
    kind: Column[PdfCertificationRequirementKind]
    logical_digest: Column[str]
    native_document_digest: Column[str]
    oracle_receipt_id: Column[str | None]
    certification_basis: Column[PdfCertificationRequirementCertificationBasis]


_read_pdf_certification_requirement_columns = cast(
    _read_pdf_certification_requirementColumns, _read_pdf_certification_requirement_function.c
)
_read_pdf_certification_requirement_statement = select(
    _read_pdf_certification_requirement_columns.lowering_identity,
    _read_pdf_certification_requirement_columns.kind,
    _read_pdf_certification_requirement_columns.logical_digest,
    _read_pdf_certification_requirement_columns.native_document_digest,
    _read_pdf_certification_requirement_columns.oracle_receipt_id,
    _read_pdf_certification_requirement_columns.certification_basis,
)


def _read_pdf_certification_requirement_result(
    row: tuple[str, str, str, str, str | None, str],
) -> PdfCertificationRequirement:
    with native_result_scope("validate_pdf_build", "PdfCertificationRequirement"):
        return PdfCertificationRequirement(
            lowering_identity=row[0],
            kind=cast(PdfCertificationRequirementKind, row[1]),
            logical_digest=row[2],
            native_document_digest=row[3],
            oracle_receipt_id=row[4],
            certification_basis=cast(PdfCertificationRequirementCertificationBasis, row[5]),
        )


def prepare_read_pdf_certification_requirement(
    *,
    build_id: str,
    task_id: TaskId,
    attempt: TaskAttempt,
    holder: str,
    frozen_digest: str,
    projection_context: PreparedRelease | None = None,
) -> Select[
    str,
    PdfCertificationRequirementKind,
    str,
    str,
    str | None,
    PdfCertificationRequirementCertificationBasis,
]:
    _request = _read_pdf_certification_requirementRequest(
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
            "read_pdf_certification_requirement",
            READ_PDF_CERTIFICATION_REQUIREMENT_CONTRACT_DIGEST,
        )
    return _read_pdf_certification_requirement_statement.params(
        **{
            "build_id": _request.build_id,
            "task_id": _request.task_id,
            "attempt": _request.attempt,
            "holder": _request.holder,
            "frozen_digest": _request.frozen_digest,
        }
    )


materialize_read_pdf_certification_requirement = _read_pdf_certification_requirement_result


def read_pdf_certification_requirement(
    conn: Connection,
    *,
    build_id: str,
    task_id: TaskId,
    attempt: TaskAttempt,
    holder: str,
    frozen_digest: str,
    projection_context: PreparedRelease | None = None,
) -> PdfCertificationRequirement:
    _statement = prepare_read_pdf_certification_requirement(
        build_id=build_id,
        task_id=task_id,
        attempt=attempt,
        holder=holder,
        frozen_digest=frozen_digest,
        projection_context=projection_context,
    )
    _native_result = conn.execute(_statement)
    with native_result_scope("validate_pdf_build", "PdfCertificationRequirement"):
        return _read_pdf_certification_requirement_result(_native_result.one())


BEGIN_PDF_ROUNDTRIP_ORACLE_CONTRACT_DIGEST = (
    "9c195e99c50997ab4cad312d3e3ac8ddcb81947e29facf7df9ffbb7c74058fdb"
)


class _begin_pdf_roundtrip_oracleRequest(OperationResult):
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


_begin_pdf_roundtrip_oracle_function = func.ops.begin_pdf_roundtrip_oracle(
    bindparam("build_id", type_=Text()),
    bindparam("task_id", type_=BigInteger()),
    bindparam("attempt", type_=BigInteger()),
    bindparam("holder", type_=Text()),
    bindparam("frozen_digest", type_=Text()),
    type_=Text(),
)
_begin_pdf_roundtrip_oracle_statement = select(_begin_pdf_roundtrip_oracle_function)


def prepare_begin_pdf_roundtrip_oracle(
    *,
    build_id: str,
    task_id: TaskId,
    attempt: TaskAttempt,
    holder: str,
    frozen_digest: str,
    projection_context: PreparedRelease | None = None,
) -> Select[str]:
    _request = _begin_pdf_roundtrip_oracleRequest(
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
            "begin_pdf_roundtrip_oracle",
            BEGIN_PDF_ROUNDTRIP_ORACLE_CONTRACT_DIGEST,
        )
    return _begin_pdf_roundtrip_oracle_statement.params(
        **{
            "build_id": _request.build_id,
            "task_id": _request.task_id,
            "attempt": _request.attempt,
            "holder": _request.holder,
            "frozen_digest": _request.frozen_digest,
        }
    )


_begin_pdf_roundtrip_oracle_adapter = TypeAdapter(str)


def materialize_begin_pdf_roundtrip_oracle(row: tuple[str]) -> str:
    with native_result_scope("validate_pdf_build", "begin_pdf_roundtrip_oracle", "value"):
        checked = _begin_pdf_roundtrip_oracle_adapter.validate_python(row[0], strict=True)
        return checked


def begin_pdf_roundtrip_oracle(
    conn: Connection,
    *,
    build_id: str,
    task_id: TaskId,
    attempt: TaskAttempt,
    holder: str,
    frozen_digest: str,
    projection_context: PreparedRelease | None = None,
) -> str:
    _statement = prepare_begin_pdf_roundtrip_oracle(
        build_id=build_id,
        task_id=task_id,
        attempt=attempt,
        holder=holder,
        frozen_digest=frozen_digest,
        projection_context=projection_context,
    )
    _native_result = conn.execute(_statement)
    with native_result_scope("validate_pdf_build", "begin_pdf_roundtrip_oracle"):
        row = _native_result.one()
        return materialize_begin_pdf_roundtrip_oracle(row)


FINISH_PDF_ROUNDTRIP_ORACLE_CONTRACT_DIGEST = (
    "001dd478bb996975557356ac0825e0cac5ad5264202d8e8f93d4c03716b39cfa"
)


class _finish_pdf_roundtrip_oracleRequest(OperationResult):
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
    oracle_receipt_id: str
    state: str
    actual_native_digest: str | None
    error_message: str | None


_finish_pdf_roundtrip_oracle_function = func.ops.finish_pdf_roundtrip_oracle(
    bindparam("build_id", type_=Text()),
    bindparam("task_id", type_=BigInteger()),
    bindparam("attempt", type_=BigInteger()),
    bindparam("holder", type_=Text()),
    bindparam("frozen_digest", type_=Text()),
    bindparam("oracle_receipt_id", type_=Text()),
    bindparam("state", type_=Text()),
    bindparam("actual_native_digest", type_=Text()),
    bindparam("error_message", type_=Text()),
)
_finish_pdf_roundtrip_oracle_statement = select(_finish_pdf_roundtrip_oracle_function)


def prepare_finish_pdf_roundtrip_oracle(
    *,
    build_id: str,
    task_id: TaskId,
    attempt: TaskAttempt,
    holder: str,
    frozen_digest: str,
    oracle_receipt_id: str,
    state: str,
    actual_native_digest: str | None,
    error_message: str | None,
    projection_context: PreparedRelease | None = None,
) -> Select[None]:
    _request = _finish_pdf_roundtrip_oracleRequest(
        build_id=build_id,
        task_id=task_id,
        attempt=attempt,
        holder=holder,
        frozen_digest=frozen_digest,
        oracle_receipt_id=oracle_receipt_id,
        state=state,
        actual_native_digest=actual_native_digest,
        error_message=error_message,
    )
    if projection_context is not None:
        require_call_context(
            projection_context,
            "validate_pdf_build",
            "finish_pdf_roundtrip_oracle",
            FINISH_PDF_ROUNDTRIP_ORACLE_CONTRACT_DIGEST,
        )
    return _finish_pdf_roundtrip_oracle_statement.params(
        **{
            "build_id": _request.build_id,
            "task_id": _request.task_id,
            "attempt": _request.attempt,
            "holder": _request.holder,
            "frozen_digest": _request.frozen_digest,
            "oracle_receipt_id": _request.oracle_receipt_id,
            "state": _request.state,
            "actual_native_digest": _request.actual_native_digest,
            "error_message": _request.error_message,
        }
    )


def finish_pdf_roundtrip_oracle(
    conn: Connection,
    *,
    build_id: str,
    task_id: TaskId,
    attempt: TaskAttempt,
    holder: str,
    frozen_digest: str,
    oracle_receipt_id: str,
    state: str,
    actual_native_digest: str | None,
    error_message: str | None,
    projection_context: PreparedRelease | None = None,
) -> None:
    _statement = prepare_finish_pdf_roundtrip_oracle(
        build_id=build_id,
        task_id=task_id,
        attempt=attempt,
        holder=holder,
        frozen_digest=frozen_digest,
        oracle_receipt_id=oracle_receipt_id,
        state=state,
        actual_native_digest=actual_native_digest,
        error_message=error_message,
        projection_context=projection_context,
    )
    _native_result = conn.execute(_statement)
    with native_result_scope("validate_pdf_build", "finish_pdf_roundtrip_oracle"):
        _native_result.scalar_one()
    return None


READ_PDF_CERTIFICATION_TARGETS_CONTRACT_DIGEST = (
    "6506a15a3df12f5b40a856c5b57446dda65e73fcb5af5f681cd05c4fb42a83da"
)


class _read_pdf_certification_targetsRequest(OperationResult):
    build_id: str
    task_id: Annotated[
        TaskId, Field(ge=TaskId(-9223372036854775808), le=TaskId(9223372036854775807))
    ]
    attempt: Annotated[
        TaskAttempt,
        Field(ge=TaskAttempt(-9223372036854775808), le=TaskAttempt(9223372036854775807)),
    ]
    holder: str
    targets: JsonValue


_read_pdf_certification_targets_function = func.ops.read_pdf_certification_targets(
    bindparam("build_id", type_=Text()),
    bindparam("task_id", type_=BigInteger()),
    bindparam("attempt", type_=BigInteger()),
    bindparam("holder", type_=Text()),
    bindparam("targets", type_=JSONB(astext_type=Text())),
    type_=BYTEA(),
)
_read_pdf_certification_targets_statement = select(_read_pdf_certification_targets_function)


def prepare_read_pdf_certification_targets(
    *,
    build_id: str,
    task_id: TaskId,
    attempt: TaskAttempt,
    holder: str,
    targets: JsonValue,
    projection_context: PreparedRelease | None = None,
) -> Select[bytes]:
    _request = _read_pdf_certification_targetsRequest(
        build_id=build_id,
        task_id=task_id,
        attempt=attempt,
        holder=holder,
        targets=targets,
    )
    if projection_context is not None:
        require_call_context(
            projection_context,
            "validate_pdf_build",
            "read_pdf_certification_targets",
            READ_PDF_CERTIFICATION_TARGETS_CONTRACT_DIGEST,
        )
    return _read_pdf_certification_targets_statement.params(
        **{
            "build_id": _request.build_id,
            "task_id": _request.task_id,
            "attempt": _request.attempt,
            "holder": _request.holder,
            "targets": _request.targets,
        }
    )


_read_pdf_certification_targets_adapter = TypeAdapter(bytes)


def materialize_read_pdf_certification_targets(row: tuple[bytes]) -> bytes:
    with native_result_scope("validate_pdf_build", "read_pdf_certification_targets", "value"):
        checked = _read_pdf_certification_targets_adapter.validate_python(row[0], strict=True)
        return checked


def read_pdf_certification_targets(
    conn: Connection,
    *,
    build_id: str,
    task_id: TaskId,
    attempt: TaskAttempt,
    holder: str,
    targets: JsonValue,
    projection_context: PreparedRelease | None = None,
) -> bytes:
    _statement = prepare_read_pdf_certification_targets(
        build_id=build_id,
        task_id=task_id,
        attempt=attempt,
        holder=holder,
        targets=targets,
        projection_context=projection_context,
    )
    _native_result = conn.execute(_statement)
    with native_result_scope("validate_pdf_build", "read_pdf_certification_targets"):
        row = _native_result.one()
        return materialize_read_pdf_certification_targets(row)


LOOKUP_PDF_VALIDATION_CONTRACT_DIGEST = (
    "241c15ffef60e4d36a9fc8c57cde7bde6e8d01c2ccd86594e64738215c2b5744"
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
    column("certification_basis", Text()),
    column("lowering_identity", Text()),
    column("attested_logical_digest", Text()),
    column("native_document_digest", Text()),
    column("oracle_receipt_id", Text()),
)


class _lookup_pdf_validationColumns(Protocol):
    build_id: Column[str]
    frozen_digest: Column[str]
    logical_digest: Column[str]
    contract_digest: Column[str]
    native_callbacks: Column[bool]
    native_contract_digest: Column[str]
    certification_basis: Column[PdfBuildValidationCertificationBasis]
    lowering_identity: Column[str]
    attested_logical_digest: Column[str]
    native_document_digest: Column[str]
    oracle_receipt_id: Column[str]


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
    _lookup_pdf_validation_columns.certification_basis,
    _lookup_pdf_validation_columns.lowering_identity,
    _lookup_pdf_validation_columns.attested_logical_digest,
    _lookup_pdf_validation_columns.native_document_digest,
    _lookup_pdf_validation_columns.oracle_receipt_id,
)


def _lookup_pdf_validation_result(
    row: tuple[str, str, str, str, bool, str, str, str, str, str, str],
) -> PdfBuildValidation:
    with native_result_scope("validate_pdf_build", "PdfBuildValidation"):
        return PdfBuildValidation(
            build_id=row[0],
            frozen_digest=row[1],
            logical_digest=row[2],
            contract_digest=row[3],
            native_callbacks=row[4],
            native_contract_digest=row[5],
            certification_basis=cast(PdfBuildValidationCertificationBasis, row[6]),
            lowering_identity=row[7],
            attested_logical_digest=row[8],
            native_document_digest=row[9],
            oracle_receipt_id=row[10],
        )


def prepare_lookup_pdf_validation(
    *,
    build_id: str,
    task_id: TaskId,
    attempt: TaskAttempt,
    holder: str,
    frozen_digest: str,
    projection_context: PreparedRelease | None = None,
) -> Select[
    str, str, str, str, bool, str, PdfBuildValidationCertificationBasis, str, str, str, str
]:
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
    return cast(
        Select[
            str, str, str, str, bool, str, PdfBuildValidationCertificationBasis, str, str, str, str
        ],
        _lookup_pdf_validation_statement.params(
            **{
                "build_id": _request.build_id,
                "task_id": _request.task_id,
                "attempt": _request.attempt,
                "holder": _request.holder,
                "frozen_digest": _request.frozen_digest,
            }
        ),
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


CHECK_PDF_BUILD_CONTRACT_DIGEST = "125613de099a96cc50e321baba7748871fab2231e64d5e85c70f2a654091984e"


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


VALIDATE_PDF_BUILD_CONTRACT_DIGEST = (
    "54ce767b23401b32a084b8abb1db8cf64b4c4bbd292011646899b25d057c6030"
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
    column("certification_basis", Text()),
    column("lowering_identity", Text()),
    column("attested_logical_digest", Text()),
    column("native_document_digest", Text()),
    column("oracle_receipt_id", Text()),
)


class _validate_pdf_buildColumns(Protocol):
    build_id: Column[str]
    frozen_digest: Column[str]
    logical_digest: Column[str]
    contract_digest: Column[str]
    native_callbacks: Column[bool]
    native_contract_digest: Column[str]
    certification_basis: Column[PdfBuildValidationCertificationBasis]
    lowering_identity: Column[str]
    attested_logical_digest: Column[str]
    native_document_digest: Column[str]
    oracle_receipt_id: Column[str]


_validate_pdf_build_columns = cast(_validate_pdf_buildColumns, _validate_pdf_build_function.c)
_validate_pdf_build_statement = select(
    _validate_pdf_build_columns.build_id,
    _validate_pdf_build_columns.frozen_digest,
    _validate_pdf_build_columns.logical_digest,
    _validate_pdf_build_columns.contract_digest,
    _validate_pdf_build_columns.native_callbacks,
    _validate_pdf_build_columns.native_contract_digest,
    _validate_pdf_build_columns.certification_basis,
    _validate_pdf_build_columns.lowering_identity,
    _validate_pdf_build_columns.attested_logical_digest,
    _validate_pdf_build_columns.native_document_digest,
    _validate_pdf_build_columns.oracle_receipt_id,
)


def _validate_pdf_build_result(
    row: tuple[str, str, str, str, bool, str, str, str, str, str, str],
) -> PdfBuildValidation:
    with native_result_scope("validate_pdf_build", "PdfBuildValidation"):
        return PdfBuildValidation(
            build_id=row[0],
            frozen_digest=row[1],
            logical_digest=row[2],
            contract_digest=row[3],
            native_callbacks=row[4],
            native_contract_digest=row[5],
            certification_basis=cast(PdfBuildValidationCertificationBasis, row[6]),
            lowering_identity=row[7],
            attested_logical_digest=row[8],
            native_document_digest=row[9],
            oracle_receipt_id=row[10],
        )


def prepare_validate_pdf_build(
    *,
    build_id: str,
    task_id: TaskId,
    attempt: TaskAttempt,
    holder: str,
    frozen_digest: str,
    projection_context: PreparedRelease | None = None,
) -> Select[
    str, str, str, str, bool, str, PdfBuildValidationCertificationBasis, str, str, str, str
]:
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
    return cast(
        Select[
            str, str, str, str, bool, str, PdfBuildValidationCertificationBasis, str, str, str, str
        ],
        _validate_pdf_build_statement.params(
            **{
                "build_id": _request.build_id,
                "task_id": _request.task_id,
                "attempt": _request.attempt,
                "holder": _request.holder,
                "frozen_digest": _request.frozen_digest,
            }
        ),
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
    "9160db3867f3f58cb90f7592f8ea60e13c7c5a2f4ee0cb0f0f388cc1a218a19a"
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
    bindparam("filters", type_=JSONB(astext_type=Text())),
    type_=JSONB(astext_type=Text()),
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


CALL_CONTRACT_DIGEST = "637287e6b320fbd61f3c01f5157905ecca3215da7826a71cf9bafc558e30ab2f"
