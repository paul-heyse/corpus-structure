"""Project-scoped immutable PDF byte storage and the fixed incoming part shape."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from enum import StrEnum
from typing import TYPE_CHECKING, Any

from pglast import ast, enums
from pglast.stream import RawStream
from sqlalchemy import CheckConstraint, Column, MetaData, Table
from sqlalchemy.dialects.postgresql import dialect
from sqlalchemy.schema import CreateTable
from sqlalchemy.sql import visitors

from corpus_structure.schema.integrity import role_name

from .native_objects import INTERNAL_PROGRAM, native_privilege_sql
from .native_program_registry import ProgramDeclaration
from .pdf_record_model import artifact_part_upload_table, record_upload_table

if TYPE_CHECKING:
    from .native_program import Statement


class PdfScratchPurpose(StrEnum):
    PART_CONTRACT = "part_contract"
    STAGE = "stage"
    COMPANION = "companion"


@dataclass(frozen=True)
class PdfScratchSpec:
    """One invocation-local relation, shared by runtime and static authoring.

    The source owns ordered columns, nullability and CHECK constraints. LIKE
    deliberately excludes keys, references, defaults and generated expressions.
    Only upload scratch admits writer COPY; the wire prototype and derived
    endpoint scratch remain private to the publisher.
    """

    purpose: PdfScratchPurpose
    source: Table
    name: str
    writer_upload: bool = False

    @property
    def owner(self) -> str:
        from .alembic_privileges import metadata_integrity

        return metadata_integrity(self.source.metadata).publisher

    @property
    def qualified_name(self) -> str:
        return "pg_temp." + self.name

    def relation(self) -> ast.RangeVar:
        return ast.RangeVar(schemaname="pg_temp", relname=self.name, inh=True)

    def create_statement(self) -> ast.CreateStmt | CreateTable:
        if self.purpose is PdfScratchPurpose.PART_CONTRACT:
            return CreateTable(self.source)
        template = (
            ast.RangeVar(schemaname="pg_temp", relname="pdf_part_wire_contract", inh=True)
            if self.source.name == "pdf_stage_artifact_part"
            else ast.RangeVar(schemaname=self.source.schema, relname=self.source.name, inh=True)
        )
        return ast.CreateStmt(
            relation=ast.RangeVar(relname=self.name, relpersistence="t", inh=True),
            tableElts=(
                ast.TableLikeClause(
                    relation=template,
                    options=enums.TableLikeOption.CREATE_TABLE_LIKE_CONSTRAINTS,
                ),
            ),
            oncommit=enums.OnCommitAction.ONCOMMIT_DROP,
        )

    def owner_statement(self) -> ast.AlterTableStmt:
        return ast.AlterTableStmt(
            relation=self.relation(),
            objtype=enums.ObjectType.OBJECT_TABLE,
            cmds=(
                ast.AlterTableCmd(
                    subtype=enums.AlterTableType.AT_ChangeOwner,
                    newowner=ast.RoleSpec(
                        roletype=enums.RoleSpecType.ROLESPEC_CSTRING, rolename=self.owner
                    ),
                ),
            ),
        )


def pdf_stage_scratch_specs(model: MetaData) -> tuple[PdfScratchSpec, ...]:
    from .pdf_staging import UPLOAD_STAGE_FAMILIES

    return tuple(
        PdfScratchSpec(PdfScratchPurpose.STAGE, relation, "ps_" + relation.name, True)
        for name in UPLOAD_STAGE_FAMILIES.values()
        for relation in (record_upload_table(name, model),)
    )


def pdf_companion_scratch_specs(model: MetaData) -> tuple[PdfScratchSpec, ...]:
    from .pdf_companion_encoding import COMPANION_STAGE_TARGETS

    return tuple(
        PdfScratchSpec(
            PdfScratchPurpose.COMPANION,
            relation,
            "pc_" + relation.name,
            relation.name != "pdf_stage_endpoint",
        )
        for name in (*COMPANION_STAGE_TARGETS.values(), "ops.pdf_stage_endpoint")
        for relation in (record_upload_table(name, model),)
    )


def pdf_scratch_specs(model: MetaData) -> tuple[PdfScratchSpec, ...]:
    contract = part_upload_contract_table(model)
    return (
        PdfScratchSpec(PdfScratchPurpose.PART_CONTRACT, contract, contract.name),
        *pdf_stage_scratch_specs(model),
        *pdf_companion_scratch_specs(model),
    )


def pdf_scratch_prepare(spec: PdfScratchSpec) -> tuple[Statement, ...]:
    """Prepare protected COPY scratch from its shared relation-purpose model."""
    from .native_program import If, Perform, Sql, call, literal, pg_type

    if spec.purpose is PdfScratchPurpose.PART_CONTRACT:
        raise ValueError("the part contract has its dedicated protected initializer")
    statements: list[Statement] = []
    is_part = spec.source.name == "pdf_stage_artifact_part"
    if is_part:
        statements.append(Perform(call("ops", "pdf_part_upload_contract")))
    reference = (
        call("ops", "pdf_part_upload_contract")
        if is_part
        else ast.TypeCast(arg=literal(spec.source.fullname), typeName=pg_type("regclass"))
    )
    statements.extend(
        (
            If(
                ast.NullTest(
                    arg=call("pg_catalog", "to_regclass", literal(spec.qualified_name)),
                    nulltesttype=enums.NullTestType.IS_NULL,
                ),
                (Sql(spec.create_statement()),),
            ),
            Perform(call("ops", "require_pdf_stage_scratch", literal(spec.name), reference)),
            Sql(
                ast.TruncateStmt(
                    relations=(spec.relation(),),
                    behavior=enums.DropBehavior.DROP_RESTRICT,
                )
            ),
        )
    )
    if spec.writer_upload:
        statements.append(
            Sql(
                ast.GrantStmt(
                    is_grant=True,
                    targtype=enums.GrantTargetType.ACL_TARGET_OBJECT,
                    objtype=enums.ObjectType.OBJECT_TABLE,
                    objects=(spec.relation(),),
                    privileges=tuple(
                        ast.AccessPriv(priv_name=name) for name in ("select", "insert")
                    ),
                    grantees=(
                        ast.RoleSpec(
                            roletype=enums.RoleSpecType.ROLESPEC_CSTRING,
                            rolename=role_name("writer"),
                        ),
                    ),
                    behavior=enums.DropBehavior.DROP_RESTRICT,
                )
            )
        )
    return tuple(statements)


def shared_streams_sql(metadata) -> str:
    from .pdf_shared_stream_queries import shared_stream_queries_sql
    from .pdf_shared_stream_writes import shared_stream_writes_sql

    return shared_stream_queries_sql(metadata) + "\n" + shared_stream_writes_sql(metadata)


def part_upload_contract_table(model: MetaData | None = None) -> Table:
    """Only a private temporary normalized wire shape, never a durable part store."""
    upload = artifact_part_upload_table(model)
    contract = Table(
        "pdf_part_wire_contract",
        MetaData(info=dict(upload.metadata.info)),
        *(Column(column.name, column.type, nullable=column.nullable) for column in upload.columns),
        prefixes=["TEMPORARY"],
        postgresql_on_commit="DROP",
    )

    def replace_column(element: Any, **_kw: Any) -> Column[Any] | None:
        return (
            contract.c[element.name]
            if isinstance(element, Column) and element.table is upload
            else None
        )

    for check in sorted(
        (check for check in upload.constraints if isinstance(check, CheckConstraint)),
        key=lambda check: str(check.name or ""),
    ):
        expression = visitors.replacement_traverse(
            check.sqltext,
            {},
            replace_column,
        )
        contract.append_constraint(CheckConstraint(expression, name=check.name))
    return contract


def part_wire_contract_programs(metadata) -> tuple[ProgramDeclaration, ...]:
    """Protect the same declared temporary contract used by native authoring."""
    from .native_program import (
        Assign,
        Block,
        If,
        Local,
        NativeRoutine,
        Perform,
        Raise,
        Return,
        Sql,
        call,
        literal,
        pg_type,
        variable,
    )

    upload = artifact_part_upload_table(metadata)
    contract = part_upload_contract_table(metadata)
    spec = PdfScratchSpec(PdfScratchPurpose.PART_CONTRACT, contract, contract.name)

    # Compare the server-normalized columns as well as owner/constraints. This
    # contract is publisher-owned, ungranted, and cannot survive this transaction.
    def text_row(values: Iterable[ast.Node]) -> ast.TypeCast:
        return ast.TypeCast(
            arg=ast.RowExpr(args=tuple(values), row_format=enums.CoercionForm.COERCE_EXPLICIT_CALL),
            typeName=pg_type("text"),
        )

    expected = ast.A_ArrayExpr(
        elements=tuple(
            text_row(
                (
                    literal(index),
                    literal(column.name),
                    ast.TypeCast(
                        arg=ast.TypeCast(
                            arg=literal(column.type.compile(dialect=dialect())),
                            typeName=pg_type("regtype"),
                        ),
                        typeName=pg_type("oid"),
                    ),
                    literal(-1),
                    literal(not column.nullable),
                    literal(""),
                    literal(""),
                )
            )
            for index, column in enumerate(upload.columns, 1)
        )
    )
    actual = ast.SubLink(
        subLinkType=enums.SubLinkType.ARRAY_SUBLINK,
        subselect=ast.SelectStmt(
            targetList=(
                ast.ResTarget(
                    val=text_row(
                        variable(name)
                        for name in (
                            "attnum",
                            "attname",
                            "atttypid",
                            "atttypmod",
                            "attnotnull",
                            "attgenerated",
                            "attidentity",
                        )
                    )
                ),
            ),
            fromClause=(ast.RangeVar(schemaname="pg_catalog", relname="pg_attribute", inh=True),),
            whereClause=ast.BoolExpr(
                boolop=enums.BoolExprType.AND_EXPR,
                args=(
                    ast.A_Expr(
                        kind=enums.A_Expr_Kind.AEXPR_OP,
                        name=(ast.String(sval="="),),
                        lexpr=variable("attrelid"),
                        rexpr=variable("contract"),
                    ),
                    ast.A_Expr(
                        kind=enums.A_Expr_Kind.AEXPR_OP,
                        name=(ast.String(sval=">"),),
                        lexpr=variable("attnum"),
                        rexpr=literal(0),
                    ),
                    ast.BoolExpr(
                        boolop=enums.BoolExprType.NOT_EXPR, args=(variable("attisdropped"),)
                    ),
                ),
            ),
            sortClause=(
                ast.SortBy(
                    node=variable("attnum"),
                    sortby_dir=enums.SortByDir.SORTBY_DEFAULT,
                    sortby_nulls=enums.SortByNulls.SORTBY_NULLS_DEFAULT,
                ),
            ),
        ),
    )
    routine = NativeRoutine(
        "ops",
        "pdf_part_upload_contract",
        parameters=(),
        returns=pg_type("regclass"),
        security_definer=True,
        search_path=("pg_catalog", "pg_temp"),
        body=Block(
            locals=(
                Local(
                    "contract",
                    pg_type("regclass"),
                    call("pg_catalog", "to_regclass", literal(spec.qualified_name)),
                ),
            ),
            statements=(
                If(
                    ast.NullTest(arg=variable("contract"), nulltesttype=enums.NullTestType.IS_NULL),
                    (
                        Sql(spec.create_statement()),
                        Assign(
                            "contract",
                            ast.TypeCast(
                                arg=literal(spec.qualified_name),
                                typeName=pg_type("regclass"),
                            ),
                        ),
                    ),
                ),
                Perform(
                    call(
                        "ops", "require_pdf_stage_scratch", literal(spec.name), variable("contract")
                    )
                ),
                If(
                    ast.A_Expr(
                        kind=enums.A_Expr_Kind.AEXPR_DISTINCT,
                        name=(ast.String(sval="="),),
                        lexpr=actual,
                        rexpr=expected,
                    ),
                    (Raise("PDF upload part contract has stale columns", "23514"),),
                ),
                Return(variable("contract")),
            ),
        ),
    )
    return (
        ProgramDeclaration(
            routine,
            "authoring/pdf-shared-streams.sql",
            role_name("publisher"),
            INTERNAL_PROGRAM,
        ),
    )


def part_wire_contract_sql(metadata) -> str:
    (program,) = part_wire_contract_programs(metadata)
    return (
        program.routine.render()
        + ";\n"
        + native_privilege_sql(program.identity, "PUBLIC", grant=False)
        + ";\n"
    )


def part_template(relation) -> str:
    from .native_program import call, literal, pg_type

    return RawStream()(
        call("ops", "pdf_part_upload_contract")
        if relation.name == "pdf_stage_artifact_part"
        else ast.TypeCast(arg=literal(relation.fullname), typeName=pg_type("regclass"))
    )


def verified_shared_stream_ids(connection, build, descriptors):
    """A probe authenticates the current build; callers cannot name another project."""
    from . import _pdf_native_calls as calls
    from .data_operation_json import json_bytes
    from .identifiers import TaskAttempt, TaskId

    rows = tuple(descriptors)
    if not rows:
        return frozenset()
    return frozenset(
        row.stream_id
        for row in calls.probe_pdf_shared_streams(
            connection,
            build_id=build.build_id,
            task_id=TaskId(build.task_id),
            attempt=TaskAttempt(build.attempt),
            holder=build.holder,
            streams=json_bytes(rows),
        )
        if row.verified
    )


class PdfSharedStreamTransfer:
    """Invocation-owned descriptor facts; every omission uses a fresh native probe."""

    def __init__(self):
        self.descriptors = {}

    def omit_verified_parts(self, connection, build, relations):
        for batch in relations.get("artifact_stream", ()):
            for row in batch.to_pylist():
                self.descriptors[row["stream_id"]] = row
        if set(relations) != {"artifact_part"}:
            return False
        ids = set()
        for batch in relations["artifact_part"]:
            if any(
                value != build.build_id
                for name in ("product_id", "revision_id")
                for value in batch.column(name).to_pylist()
            ):
                raise ValueError("shared part replay changes its owned build")
            ids.update(batch.column("stream_id").to_pylist())
        if not ids or not ids <= self.descriptors.keys():
            return False
        return ids <= verified_shared_stream_ids(
            connection, build, (self.descriptors[key] for key in sorted(ids))
        )
