"""Typed historical-byte transformation against the fixed N2 predecessor.

Only the retired input shapes come from the immutable predecessor witness. Every
surviving relation comes from the current physical model. The generated program
is frozen by the ordinary native revision lifecycle before it can execute.
"""

from __future__ import annotations

import ast as python_ast
from hashlib import sha256
from pathlib import Path

from pglast import ast, enums
from sqlalchemy import BigInteger, Column, LargeBinary, MetaData, Table, Text
from sqlalchemy import and_, cast, exists, func, literal, or_, select, tuple_, union_all, update
from sqlalchemy.dialects.postgresql import insert

from corpus_structure.semantic.metadata import table
from corpus_structure.semantic.native_admission import _admission_descriptor
from corpus_structure.semantic.native_program import (
    Assign,
    Block,
    Do,
    ForQuery,
    If,
    Local,
    Raise,
    SelectInto,
    Sql,
    While,
    core_variable,
    pg_type,
)

RETIRED_PARTS = ("ops.pdf_artifact_part", "ops.pdf_stage_artifact_part")
S40_RELATIONS = (
    "ops.pdf_stage_build",
    "ops.pdf_artifact_stream",
    "ops.pdf_stage_artifact_stream",
    "ops.pdf_shared_stream",
    "ops.pdf_shared_stream_part",
    "ops.pdf_shared_stream_verification",
)
_PREDECESSOR = "semantic_ddo_pe_n2"


def predecessor_parts() -> tuple[dict[str, Table], bytes]:
    """Authenticate and project the fixed predecessor's captured physical facts.

    This maintenance owner is deliberately N2-specific: it neither reflects live
    tables nor guesses a predecessor shape from the current upload contract.
    """
    versions = Path(__file__).resolve().parents[3] / "target_alembic" / "versions"
    revision = versions / f"{_PREDECESSOR}.py"
    fields = {}
    for node in python_ast.parse(revision.read_bytes()).body:
        if isinstance(node, python_ast.Assign) and len(node.targets) == 1:
            target = node.targets[0]
            if isinstance(target, python_ast.Name) and target.id in {
                "revision", "NATIVE_ADMISSION_FILE", "NATIVE_ADMISSION_SHA256"
            }:
                fields[target.id] = python_ast.literal_eval(node.value)
    if fields.get("revision") != _PREDECESSOR:
        raise ValueError("S40 requires the fixed N2 predecessor witness")
    filename = fields["NATIVE_ADMISSION_FILE"]
    if not isinstance(filename, str) or Path(filename).name != filename:
        raise ValueError("S40 predecessor has an invalid admission artifact")
    source = (versions / filename).read_bytes()
    if sha256(source).hexdigest() != fields["NATIVE_ADMISSION_SHA256"]:
        raise ValueError("S40 predecessor admission artifact differs from its frozen digest")
    inventory = _admission_descriptor(source.decode())["tables"]
    shapes = {item["relation"]: item for item in inventory if item["relation"] in RETIRED_PARTS}
    if set(shapes) != set(RETIRED_PARTS):
        raise ValueError("S40 predecessor lacks both retired part relations")
    types = {"text": Text, "bigint": BigInteger, "bytea": LargeBinary}
    metadata = MetaData()
    relations = {}
    for name in RETIRED_PARTS:
        shape = shapes[name]
        if shape["owner"] != "corpus_sem_publisher":
            raise ValueError("S40 predecessor part ownership differs")
        schema, relation = name.split(".")
        relations[name] = Table(
            relation,
            metadata,
            *(
                Column(
                    item["name"], types[item["type"]](), nullable=not item["not_null"],
                    primary_key=item["name"] in shape["primary_key"],
                )
                for item in shape["columns"]
            ),
            schema=schema,
        )
    return relations, source


def _range(relation: Table) -> ast.RangeVar:
    return ast.RangeVar(schemaname=str(relation.schema), relname=relation.name, inh=True)


def _refusal(message: str) -> tuple[Raise, ...]:
    return (Raise(message, "23514"),)


def _content_trigger(relation: Table, *, enabled: bool) -> Sql:
    return Sql(
        ast.AlterTableStmt(
            relation=_range(relation),
            cmds=(ast.AlterTableCmd(
                subtype=(enums.AlterTableType.AT_EnableTrig if enabled else enums.AlterTableType.AT_DisableTrig),
                name="pdf_shared_content_mutation",
            ),),
            objtype=enums.ObjectType.OBJECT_TABLE,
        )
    )


def shared_stream_program(parts: dict[str, Table]) -> str:
    """Preserve actual sealed bytes, refusing inconsistent historical inventory."""
    build = table("ops.pdf_stage_build")
    streams = table("ops.pdf_shared_stream")
    stored = table("ops.pdf_shared_stream_part")
    verification = table("ops.pdf_shared_stream_verification")
    stage = table("ops.pdf_stage_artifact_stream")
    final = table("ops.pdf_artifact_stream")
    def descriptor(name: str):
        return core_variable("descriptor", stage.c[name].type, name)

    def part(name: str):
        return core_variable("part", parts[RETIRED_PARTS[0]].c[name].type, name)

    def owner(name: str):
        return core_variable("owner", build.c[name].type, name)

    def retained(name: str):
        return core_variable("retained", stored.c[name].type, name)
    project = core_variable("project", streams.c.project_id.type)
    state = core_variable("state", LargeBinary())
    pending = core_variable("pending", LargeBinary())
    block = core_variable("block", LargeBinary())
    block_ordinal = core_variable("block_ordinal", BigInteger())
    offset = core_variable("offset_", BigInteger())
    next_ordinal = core_variable("next_ordinal", BigInteger())

    def key(relation: Table, *, length: str = "byte_length"):
        return and_(
            relation.c.project_id == project,
            relation.c.encoding_profile == descriptor("encoding_profile"),
            relation.c[length] == descriptor("byte_length"),
            relation.c.byte_root == descriptor("byte_root"),
        )

    block_digest = func.pg_catalog.encode(func.pg_catalog.sha256(block), "hex")
    canonical = (
        block_ordinal * 65536, func.pg_catalog.octet_length(block), block, block_digest
    )
    block_body = (
        Assign("block", func.pg_catalog.substr(pending, 1, 65536)),
        Assign("pending", func.pg_catalog.substr(pending, 65537)),
        Sql(insert(stored).values(
            project_id=project,
            encoding_profile=descriptor("encoding_profile"),
            stream_length=descriptor("byte_length"),
            byte_root=descriptor("byte_root"),
            ordinal=block_ordinal,
            byte_offset=canonical[0], byte_length=canonical[1], body=block,
            sha256_digest=block_digest,
        ).on_conflict_do_nothing()),
        SelectInto(
            select(stored).where(key(stored, length="stream_length"), stored.c.ordinal == block_ordinal),
            ("retained",), strict=True,
        ),
        If(
            tuple_(*(retained(name) for name in ("byte_offset", "byte_length", "body", "sha256_digest")))
            .is_distinct_from(tuple_(*canonical)),
            _refusal("S40 historical copies disagree on shared bytes; regenerate them"),
        ),
        Assign("state", func.ops.pdf_identity_fold_step(state, block_ordinal, block)),
        Assign("block_ordinal", block_ordinal + 1),
    )
    part_body = (
        If(or_(
            part("ordinal") != next_ordinal,
            part("byte_offset") != offset,
            ~part("byte_length").between(1, 65536),
            part("byte_length") != func.pg_catalog.octet_length(part("body")),
            part("sha256_digest") != func.pg_catalog.encode(func.pg_catalog.sha256(part("body")), "hex"),
        ), _refusal("S40 historical actual part inventory differs; regenerate it")),
        Assign("pending", pending.op("||")(part("body"))),
        Assign("offset_", offset + part("byte_length")),
        Assign("next_ordinal", next_ordinal + 1),
        While(or_(
            func.pg_catalog.octet_length(pending) >= 65536,
            and_(offset == descriptor("byte_length"), func.pg_catalog.octet_length(pending) > 0),
        ), block_body),
    )

    def copy_parts(relation: Table) -> ForQuery:
        return ForQuery(
            ("part",),
            select(*(relation.c[name] for name in (
                "ordinal", "byte_offset", "byte_length", "body", "sha256_digest"
            ))).where(*(
                relation.c[name] == descriptor(name)
                for name in ("product_id", "revision_id", "stream_id")
            )).order_by(relation.c.ordinal),
            part_body,
        )

    descriptor_body = (
        If(descriptor("product_id").is_distinct_from(descriptor("revision_id")),
           _refusal("S40 generated revision needs explicit regeneration")),
        SelectInto(select(build).where(build.c.build_id == descriptor("product_id")), ("owner",)),
        Assign("project", func.ops.pdf_stream_project(descriptor("product_id"))),
        If(or_(owner("build_id").is_(None), project.is_(None)),
           _refusal("S40 generated stream lacks actual declared build/project; regenerate it")),
        Sql(insert(streams).values(
            project_id=project,
            encoding_profile=descriptor("encoding_profile"),
            byte_length=descriptor("byte_length"), byte_root=descriptor("byte_root"),
            owner_build_id=owner("build_id"), owner_attempt=owner("attempt"), owner_holder=owner("holder"),
        ).on_conflict_do_nothing()),
        Assign("state", func.ops.pdf_identity_fold_start("bytes")),
        Assign("pending", cast(literal(b"", type_=LargeBinary()), LargeBinary())),
        Assign("block_ordinal", literal(0)),
        Assign("offset_", literal(0)),
        Assign("next_ordinal", literal(0)),
        If(core_variable("descriptor", Text(), "source") == "stage",
           (copy_parts(parts["ops.pdf_stage_artifact_part"]),),
           (copy_parts(parts["ops.pdf_artifact_part"]),)),
        If(or_(
            offset != descriptor("byte_length"),
            func.pg_catalog.octet_length(pending) != 0,
            func.pg_catalog.encode(func.ops.pdf_identity_fold_finish(state, block_ordinal, offset), "hex")
            != descriptor("byte_root"),
        ), _refusal("S40 historical actual byte fold differs; regenerate it")),
        If(select(func.count()).select_from(stored).where(key(stored, length="stream_length"))
           .scalar_subquery() != block_ordinal,
           _refusal("S40 shared byte inventory has extra parts")),
        Sql(insert(verification).values(
            project_id=project, encoding_profile=descriptor("encoding_profile"),
            byte_length=descriptor("byte_length"), byte_root=descriptor("byte_root"),
            part_count=block_ordinal,
        ).on_conflict_do_nothing()),
    )

    def descriptors(source: str, relation: Table):
        return select(literal(source).label("source"), *relation.c).where(exists(
            select(1).select_from(build).where(
                build.c.build_id == relation.c.product_id,
                build.c.state.in_(("frozen", "published")),
            )
        ))

    population = union_all(descriptors("stage", stage), descriptors("final", final)).subquery("descriptors")
    return Do(Block(
        (
            # An OPEN producer was never admitted. Its source assets and spool
            # remain available for regeneration after append capability closes.
            Sql(update(build).where(build.c.state == "open").values(state="abandoned")),
            Sql(ast.LockStmt(
                relations=tuple(_range(relation) for relation in (
                    parts[RETIRED_PARTS[0]], parts[RETIRED_PARTS[1]], final, stage
                )), mode=8, nowait=False,
            )),
            _content_trigger(stored, enabled=False),
            ForQuery(("descriptor",), select(population).order_by(
                population.c.product_id, population.c.revision_id,
                population.c.stream_id, population.c.source,
            ), descriptor_body),
            _content_trigger(stored, enabled=True),
        ),
        locals=(
            Local("descriptor", pg_type("record")),
            Local("part", pg_type("record")), Local("owner", build),
            Local("project", pg_type("text")),
            *(Local(name, pg_type("bytea")) for name in ("state", "pending", "block")),
            *(Local(name, pg_type("bigint")) for name in ("block_ordinal", "offset_", "next_ordinal")),
            Local("retained", stored),
        ),
    ))
