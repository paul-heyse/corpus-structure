"""Closed revision-owned data transformations, frozen before migration execution.

Requests select a first-party builder, never a Python import or SQL fragment.
Previews retain its source/dependency identity and compiled named-column SQL.
Frozen revisions execute ordinary Alembic operations without importing builders.
"""

from __future__ import annotations

from copy import copy
from hashlib import sha256
from importlib.metadata import version
from pathlib import Path
from typing import TYPE_CHECKING, Literal

from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import Text, column, exists, func, or_, select, table, update
from sqlalchemy.dialects.postgresql import dialect

if TYPE_CHECKING:
    from alembic.operations.ops import MigrateOperation, UpgradeOps
    from sqlalchemy.sql import ClauseElement, Select

    from corpus_structure.semantic.native_objects import NativeAuthoring


class N1Parameters(BaseModel):
    """Closed maintenance owners accept no caller-supplied evidence or SQL."""

    model_config = ConfigDict(extra="forbid", frozen=True)


class DataStepRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    name: Literal["ddo_n1_relower", "pdf_s40_shared_streams"]
    parameters: N1Parameters = Field(default_factory=N1Parameters)


class FrozenDataStep(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    name: Literal["ddo_n1_relower", "pdf_s40_shared_streams"]
    owner: Literal["corpus_sem_publisher"] = "corpus_sem_publisher"
    implementation_sha256: str
    libraries: tuple[tuple[str, str], ...]
    statements: tuple[str, ...]
    deferred_columns: tuple[tuple[str, str], ...]
    guarded_relations: tuple[str, ...]


_N1_COLUMNS = (
    ("sem.data_operation_release", "lowering_digest"),
    *(
        ("sem.data_operation_definition", name)
        for name in (
            "binding_expression",
            "definition_identity",
            "eligibility_identity",
            "quantified",
            "dependencies",
        )
    ),
    ("sem.runtime_binding", "execution_profile"),
    ("ops.data_population", "context_key"),
)


def _sql(statement: ClauseElement) -> str:
    return str(
        statement.compile(
            dialect=dialect(paramstyle="named"), compile_kwargs={"literal_binds": True}
        )
    )


def _refuse_rows(query: Select, message: str) -> str:
    # Both the query and message are first-party authoring, never request SQL.
    return (
        "DO $data_step$ BEGIN IF EXISTS ("
        + _sql(query)
        + ") THEN RAISE EXCEPTION '"
        + message
        + "' USING ERRCODE='23514'; END IF; END $data_step$"
    )


def _n1() -> FrozenDataStep:
    definitions = table(
        "data_operation_definition",
        column("release_id", Text),
        *(
            column(name)
            for relation, name in _N1_COLUMNS
            if relation == "sem.data_operation_definition"
        ),
        schema="sem",
    )
    finalized = table("release_finalization", column("release_id", Text), schema="sem")
    releases = (
        select(definitions.c.release_id)
        .join(finalized, finalized.c.release_id == definitions.c.release_id)
        .distinct()
        .subquery("admitted_releases")
    )
    relower = select(func.sem.relower_admitted_data_operation_release(releases.c.release_id))
    population = table("data_population", column("evidence"), column("context_key"), schema="ops")
    context_key = func.ops.ddo_digest(func.ops.ddo_population_evidence_scope(population.c.evidence))
    populations = (
        update(population)
        .values(context_key=context_key)
        .where(population.c.context_key.is_distinct_from(context_key))
    )
    headers = table(
        "data_operation_release",
        column("release_id", Text),
        column("lowering_digest", Text),
        schema="sem",
    )
    runtimes = table(
        "runtime_binding",
        column("release_id", Text),
        column("execution_profile", Text),
        schema="sem",
    )
    missing_header = select(releases.c.release_id).where(
        ~exists(
            select(1)
            .select_from(headers)
            .where(
                headers.c.release_id == releases.c.release_id,
                headers.c.lowering_digest.is_not(None),
            )
        )
    )
    missing_definition = select(definitions.c.release_id).where(
        or_(
            *(
                definitions.c[name].is_(None)
                for relation, name in _N1_COLUMNS
                if relation == "sem.data_operation_definition"
            )
        )
    )
    missing_runtime = select(runtimes.c.release_id).where(
        or_(runtimes.c.execution_profile.is_(None), runtimes.c.execution_profile == "")
    )
    return FrozenDataStep(
        name="ddo_n1_relower",
        implementation_sha256=sha256(Path(__file__).read_bytes()).hexdigest(),
        libraries=tuple((name, version(name)) for name in ("sqlalchemy", "alembic")),
        statements=(
            _sql(relower),
            _sql(populations),
            _refuse_rows(
                missing_header, "N1 re-lowering left an admitted release without lowering facts"
            ),
            _refuse_rows(missing_definition, "N1 re-lowering left incomplete operation facts"),
            _refuse_rows(missing_runtime, "N1 re-lowering left an absent runtime profile"),
            _refuse_rows(
                select(population.c.context_key).where(population.c.context_key.is_(None)),
                "N1 re-lowering left an absent population context",
            ),
        ),
        deferred_columns=_N1_COLUMNS,
        guarded_relations=(
            "sem.data_operation_definition",
            "sem.data_operation_release",
            "sem.runtime_binding",
            "ops.data_population",
        ),
    )


_S40_RETIRED_PARTS = ("ops.pdf_artifact_part", "ops.pdf_stage_artifact_part")


def _pdf_s40() -> FrozenDataStep:
    source = Path(__file__).with_name("sql").joinpath("pdf_s40_shared_streams.sql").read_bytes()
    identity = sha256(sha256(Path(__file__).read_bytes()).digest() + sha256(source).digest()).hexdigest()
    return FrozenDataStep(
        name="pdf_s40_shared_streams", implementation_sha256=identity,
        libraries=tuple((name, version(name)) for name in ("sqlalchemy", "alembic")),
        statements=(source.decode(),), deferred_columns=(), guarded_relations=(),
    )


def prepare_data_steps(requests: tuple[DataStepRequest, ...]) -> tuple[FrozenDataStep, ...]:
    if len({request.name for request in requests}) != len(requests):
        raise ValueError("duplicate revision data step")
    # The closed DTO and this finite map are the only builder selection surface.
    builders = {"ddo_n1_relower": _n1, "pdf_s40_shared_streams": _pdf_s40}
    return tuple(builders[request.name]() for request in requests)


def order_data_steps(
    upgrade_ops: UpgradeOps, steps: tuple[FrozenDataStep, ...], authoring: NativeAuthoring
) -> None:
    """Stage nullable DDL, native helpers, authenticated data, then final constraints."""
    from alembic.operations import ops

    from corpus_structure.semantic.alembic_native import NativeTransitionOp
    from corpus_structure.semantic.alembic_privileges import OwnedOperationsOp
    from corpus_structure.semantic.native_objects import NativeAuthoringError

    if not steps:
        return
    if steps != prepare_data_steps(tuple(DataStepRequest(name=step.name) for step in steps)):
        raise NativeAuthoringError("revision data steps differ from current closed builder custody")
    deferred = {entry for step in steps for entry in step.deferred_columns}
    final: list[MigrateOperation] = []
    retired_parts = set(_S40_RETIRED_PARTS) if any(step.name == "pdf_s40_shared_streams" for step in steps) else set()
    final_drops: list[MigrateOperation] = []

    def prepare(operation: MigrateOperation) -> MigrateOperation | None:
        if isinstance(operation, OwnedOperationsOp):
            operation.ops = [
                staged for child in operation.ops if (staged := prepare(child)) is not None
            ]
            return operation if operation.ops else None
        if isinstance(operation, ops.DropTableOp) and f"{operation.schema}.{operation.table_name}" in retired_parts:
            final_drops.append(OwnedOperationsOp("corpus_sem_publisher", [operation]))
            return None
        if isinstance(operation, ops.AddColumnOp):
            relation = f"{operation.schema}.{operation.table_name}"
            source = operation.column
            if (relation, source.name) in deferred and not source.nullable:
                if (
                    source.primary_key
                    or source.constraints
                    or source.foreign_keys
                    or source.identity
                    or source.computed
                ):
                    raise NativeAuthoringError(
                        "data-step nullable staging requires a plain added column"
                    )
                # A shallow copy changes only nullable and preserves all authored
                # column facets without mutating the target metadata's column.
                staged = copy(source)
                staged.nullable = True
                operation = copy(operation)
                operation.column = staged
                final.append(
                    OwnedOperationsOp(
                        "corpus_sem_publisher",
                        [
                            ops.AlterColumnOp(
                                operation.table_name,
                                source.name,
                                schema=operation.schema,
                                existing_type=source.type,
                                existing_nullable=True,
                                modify_nullable=False,
                            )
                        ],
                    )
                )
        elif isinstance(operation, ops.AlterColumnOp):
            relation = f"{operation.schema}.{operation.table_name}"
            if (relation, operation.column_name) in deferred and operation.modify_nullable is False:
                final.append(
                    OwnedOperationsOp(
                        "corpus_sem_publisher",
                        [
                            ops.AlterColumnOp(
                                operation.table_name,
                                operation.column_name,
                                schema=operation.schema,
                                existing_type=operation.modify_type
                                if operation.modify_type is not None
                                else operation.existing_type,
                                existing_nullable=True,
                                modify_nullable=False,
                            )
                        ],
                    )
                )
                # Type/default/comment changes must precede row-type-dependent
                # helper installation. Defer only the NOT NULL effect.
                staged = copy(operation)
                staged.modify_nullable = None
                return staged if staged.has_changes() else None
        return operation

    guarded = {relation for step in steps for relation in step.guarded_relations}
    guards = {
        f"{item.identity.schema}.{item.identity.relation}": item
        for item in authoring.desired
        if item.identity.kind == "trigger"
        and item.identity.name == "semantic_immutable"
        and f"{item.identity.schema}.{item.identity.relation}" in guarded
    }
    if set(guards) != guarded:
        raise NativeAuthoringError("revision data step lacks exact intrinsic guard material")
    upgrade_ops.ops[:] = [
        staged for operation in upgrade_ops.ops if (staged := prepare(operation)) is not None
    ]
    upgrade_ops.ops.extend(NativeTransitionOp(guards[name], None) for name in sorted(guards))
    upgrade_ops.ops.extend(
        OwnedOperationsOp(
            step.owner, [ops.ExecuteSQLOp(statement) for statement in step.statements]
        )
        for step in steps
    )
    upgrade_ops.ops.extend(final_drops)
    upgrade_ops.ops.extend(final)
    upgrade_ops.ops.extend(NativeTransitionOp(None, guards[name]) for name in sorted(guards))
