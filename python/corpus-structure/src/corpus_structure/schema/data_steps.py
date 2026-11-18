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
from typing import TYPE_CHECKING, Literal, get_args

from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import delete, exists, func, or_, select, update
from sqlalchemy.dialects.postgresql import dialect

from corpus_structure.schema.integrity import role_name

if TYPE_CHECKING:
    from alembic.operations.ops import MigrateOperation, UpgradeOps
    from sqlalchemy import MetaData
    from sqlalchemy.sql import ClauseElement, Select

    from corpus_structure.semantic.native_objects import NativeAuthoring


class N1Parameters(BaseModel):
    """Closed maintenance owners accept no caller-supplied evidence or SQL."""

    model_config = ConfigDict(extra="forbid", frozen=True)


class DataStepRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    name: Literal["ddo_n1_relower", "pdf_s36_retire_validation", "pdf_s40_shared_streams"]
    parameters: N1Parameters = Field(default_factory=N1Parameters)


class FrozenDataStep(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    name: Literal["ddo_n1_relower", "pdf_s36_retire_validation", "pdf_s40_shared_streams"]
    owner: Literal["corpus_sem_publisher"] = "corpus_sem_publisher"
    implementation_sha256: str
    libraries: tuple[tuple[str, str], ...]
    statements: tuple[str, ...]
    deferred_columns: tuple[tuple[str, str], ...]
    deferred_foreign_keys: tuple[tuple[str, str], ...] = ()
    guarded_relations: tuple[str, ...]
    prerequisite_relations: tuple[str, ...]
    retired_relations: tuple[str, ...]


if get_args(FrozenDataStep.model_fields["owner"].annotation) != (role_name("publisher"),):
    raise ValueError("frozen data-step owner type disagrees with the integrity vocabulary")


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
    from corpus_structure.semantic.native_program import Block, Do, If, Raise

    return Do(Block((If(exists(query), (Raise(message, "23514"),)),)))


def _implementation_id(*sources: bytes) -> str:
    from corpus_structure.semantic import native_program

    digest = sha256()
    for source in (
        Path(__file__).read_bytes(),
        Path(native_program.__file__).read_bytes(),
        *sources,
    ):
        digest.update(sha256(source).digest())
    return digest.hexdigest()


def _libraries() -> tuple[tuple[str, str], ...]:
    return tuple((name, version(name)) for name in ("sqlalchemy", "alembic", "pglast"))


def _n1(target: MetaData, predecessor: str | None) -> FrozenDataStep:
    table = target.tables.__getitem__

    definitions = table("sem.data_operation_definition")
    finalized = table("sem.release_finalization")
    releases = (
        select(definitions.c.release_id)
        .join(finalized, finalized.c.release_id == definitions.c.release_id)
        .distinct()
        .subquery("admitted_releases")
    )
    relower = select(func.sem.relower_admitted_data_operation_release(releases.c.release_id))
    population = table("ops.data_population")
    context_key = func.ops.ddo_digest(func.ops.ddo_population_evidence_scope(population.c.evidence))
    populations = (
        update(population)
        .values(context_key=context_key)
        .where(population.c.context_key.is_distinct_from(context_key))
    )
    headers = table("sem.data_operation_release")
    runtimes = table("sem.runtime_binding")
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
        implementation_sha256=_implementation_id(),
        libraries=_libraries(),
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
        prerequisite_relations=tuple(
            sorted(
                (
                    definitions.fullname,
                    finalized.fullname,
                    population.fullname,
                    headers.fullname,
                    runtimes.fullname,
                )
            )
        ),
        retired_relations=(),
    )


_S36_COLUMNS = tuple(
    ("ops.pdf_build_validation", name)
    for name in (
        "certification_basis",
        "lowering_identity",
        "attested_logical_digest",
        "native_document_digest",
        "oracle_receipt_id",
    )
)


def _pdf_s36(target: MetaData, predecessor: str | None) -> FrozenDataStep:
    """Retire unqualified receipts, never invent historical producer attestations.

    Products and their original/record bytes remain retained. A historical product
    without current certification is inert and must be regenerated for current use.
    """
    validation = target.tables["ops.pdf_build_validation"]
    unqualified = or_(*(validation.c[name].is_(None) for _, name in _S36_COLUMNS))
    return FrozenDataStep(
        name="pdf_s36_retire_validation",
        implementation_sha256=_implementation_id(),
        libraries=_libraries(),
        statements=(
            _sql(delete(validation).where(unqualified)),
            _refuse_rows(
                select(1).select_from(validation).where(unqualified),
                "S36 retained an unqualified validation receipt",
            ),
        ),
        deferred_columns=_S36_COLUMNS,
        deferred_foreign_keys=((validation.fullname, "ops.pdf_producer_certification"),),
        guarded_relations=("ops.pdf_build_validation",),
        prerequisite_relations=(validation.fullname,),
        retired_relations=(),
    )


def _pdf_s40(target: MetaData, predecessor: str | None) -> FrozenDataStep:
    from . import data_step_programs

    parts, witness = data_step_programs.predecessor_parts(predecessor)
    return FrozenDataStep(
        name="pdf_s40_shared_streams",
        implementation_sha256=_implementation_id(
            Path(data_step_programs.__file__).read_bytes(), witness
        ),
        libraries=_libraries(),
        statements=(data_step_programs.shared_stream_program(parts, target),),
        deferred_columns=(),
        guarded_relations=(),
        prerequisite_relations=tuple(sorted((*data_step_programs.S40_RELATIONS, *parts))),
        retired_relations=data_step_programs.RETIRED_PARTS,
    )


def prepare_data_steps(
    requests: tuple[DataStepRequest, ...], *, target: MetaData, predecessor: str | None
) -> tuple[FrozenDataStep, ...]:
    if len({request.name for request in requests}) != len(requests):
        raise ValueError("duplicate revision data step")
    # The closed DTO and this finite map are the only builder selection surface.
    builders = {
        "ddo_n1_relower": _n1,
        "pdf_s36_retire_validation": _pdf_s36,
        "pdf_s40_shared_streams": _pdf_s40,
    }
    return tuple(builders[request.name](target, predecessor) for request in requests)


def order_data_steps(
    upgrade_ops: UpgradeOps,
    steps: tuple[FrozenDataStep, ...],
    authoring: NativeAuthoring,
    *,
    target: MetaData,
    predecessor: str | None,
) -> None:
    """Stage nullable DDL, native helpers, authenticated data, then final constraints."""
    from alembic.operations import ops

    from corpus_structure.semantic.alembic_native import NativeTransitionOp
    from corpus_structure.semantic.alembic_privileges import OwnedOperationsOp
    from corpus_structure.semantic.native_objects import NativeAuthoringError

    if not steps:
        return
    if steps != prepare_data_steps(
        tuple(DataStepRequest(name=step.name) for step in steps),
        target=target,
        predecessor=predecessor,
    ):
        raise NativeAuthoringError("revision data steps differ from current closed builder custody")
    deferred = {entry for step in steps for entry in step.deferred_columns}
    final: list[MigrateOperation] = []
    retired_relations = {relation for step in steps for relation in step.retired_relations}
    final_drops: list[MigrateOperation] = []
    captured_retirements: set[str] = set()

    def prepare(operation: MigrateOperation) -> MigrateOperation | None:
        if isinstance(operation, OwnedOperationsOp):
            operation.ops = [
                staged for child in operation.ops if (staged := prepare(child)) is not None
            ]
            return operation if operation.ops else None
        if (
            isinstance(operation, ops.DropTableOp)
            and f"{operation.schema}.{operation.table_name}" in retired_relations
        ):
            relation = f"{operation.schema}.{operation.table_name}"
            if relation in captured_retirements:
                raise NativeAuthoringError("revision data step repeats a retired relation")
            captured_retirements.add(relation)
            final_drops.append(OwnedOperationsOp(role_name("publisher"), [operation]))
            return None
        if isinstance(operation, ops.AddColumnOp):
            relation = f"{operation.schema}.{operation.table_name}"
            source = operation.column
            if (relation, source.name) in deferred and not source.nullable:
                if source.primary_key or source.constraints or source.identity or source.computed:
                    raise NativeAuthoringError(
                        f"data-step nullable staging requires a plain added column: {relation}.{source.name}"
                    )
                # SQLAlchemy clones and rebinds foreign keys independently. A
                # shallow copy would share their parent with the target column.
                staged = source._copy()
                staged.nullable = True
                operation = copy(operation)
                operation.column = staged
                final.append(
                    OwnedOperationsOp(
                        role_name("publisher"),
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
                        role_name("publisher"),
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
    if captured_retirements != retired_relations:
        raise NativeAuthoringError("revision data step lacks its declared physical retirement")
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
