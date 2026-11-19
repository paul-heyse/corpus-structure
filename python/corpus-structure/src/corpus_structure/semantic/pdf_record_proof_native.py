"""Published proof reads over exact immutable record placement."""

from sqlalchemy import BigInteger, MetaData, Text, column, func, literal, select, true
from sqlalchemy.dialects.postgresql import JSONB

from corpus_structure.schema.integrity import role_name

from .native_objects import NativeProgramAccess, native_privilege_sql, native_sql_script
from .native_program import NativeRoutine, Parameter, column_type, core_variable, pg_type
from .native_program_registry import ProgramDeclaration


def pdf_record_proof_programs(model: MetaData) -> tuple[ProgramDeclaration, ...]:
    placement = model.tables["ops.pdf_published_revision"]
    pin = (
        ("p_task", placement.c.task_id),
        ("p_key", placement.c.product_key),
        ("p_digest", placement.c.logical_digest),
    )
    parameters = tuple(Parameter(name, column_type(field)) for name, field in pin)
    pin_values = (core_variable(name, field.type) for name, field in pin)
    published = (
        func.ops.read_pdf_published_revision(*pin_values)
        .table_valued(column("build_id", placement.c.build_id.type))
        .alias("p")
    )
    frames = (
        func.ops.pdf_record_identity_frames(published.c.build_id, published.c.build_id, False)
        .table_valued(column("frame"))
        .render_derived()
        .lateral("f")
    )
    access = model.tables["kb.pdf_record_access"].alias("a")
    records = model.tables["kb.pdf_record_native"].alias("n")
    members = model.tables["kb.pdf_record_membership"].alias("m")

    def under(row, pin):
        return (row.c.product_id == pin.c.build_id) & (row.c.revision_id == pin.c.build_id)

    items = (
        select(
            access.c.pointer,
            records.c.record_id,
            access.c.label,
            access.c.content_layer,
            access.c.parent_pointer,
            access.c.native_json["children"].label("children"),
        )
        .select_from(
            published.join(access, under(access, published)).join(
                records, under(records, published) & (records.c.native_address == access.c.pointer)
            )
        )
        .order_by(access.c.pointer.collate("C"))
    )
    build = select(published.c.build_id).cte("published").prefix_with("MATERIALIZED")
    fields = (
        func.jsonb_each(records.c.structure_json["fields"])
        .table_valued(column("key", Text()), column("value", JSONB()))
        .lateral("f")
    )
    targets = (
        select(
            records.c.record_id.label("owner"),
            fields.c.key.label("field"),
            literal(-1, type_=BigInteger()).label("member_position"),
            fields.c.value["target"].astext.label("target"),
        )
        .select_from(build.join(records, under(records, build)).join(fields, true()))
        .where(fields.c.value["kind"].astext == "object")
        .union_all(
            select(
                members.c.parent_id, members.c.field_name, members.c.ordinal, members.c.record_id
            )
            .select_from(build.join(members, under(members, build)))
            .where(
                members.c.value_kind == "record",
                members.c.member_key.is_(None),
                members.c.member_key_stream_id.is_(None),
            )
        )
    )
    programs = []
    for name, query, datatype, columns in (
        (
            "read_pdf_record_identity_frames",
            select(frames.c.frame).select_from(published.join(frames, true())),
            "bytea",
            (),
        ),
        (
            "read_pdf_record_identity_items",
            items,
            "record",
            (
                ("pointer", column_type(access.c.pointer)),
                ("record_id", column_type(records.c.record_id)),
                ("label", column_type(access.c.label)),
                ("content_layer", column_type(access.c.content_layer)),
                ("parent_pointer", column_type(access.c.parent_pointer)),
                ("children", pg_type("jsonb")),
            ),
        ),
        (
            "read_pdf_record_identity_targets",
            targets,
            "record",
            (
                ("owner", column_type(records.c.record_id)),
                ("field", pg_type("text")),
                ("member_position", column_type(members.c.ordinal)),
                ("target", column_type(records.c.record_id)),
            ),
        ),
    ):
        returns = pg_type(datatype)
        returns.setof = True
        routine = NativeRoutine(
            "ops",
            name,
            parameters=parameters,
            returns=returns,
            body=query,
            table_columns=columns,
            security_definer=True,
            search_path=("pg_catalog", "pg_temp"),
            volatility="stable",
        )
        programs.append(
            ProgramDeclaration(
                routine,
                "authoring/pdf-record-proof.sql",
                role_name("publisher"),
                NativeProgramAccess(purposes=("read", "evaluate")),
            )
        )
    return tuple(programs)


def pdf_record_proof_sql(model: MetaData) -> str:
    return native_sql_script(
        statement
        for program in pdf_record_proof_programs(model)
        for statement in (
            program.routine.render(),
            native_privilege_sql(program.identity, "PUBLIC", grant=False),
            *(
                native_privilege_sql(program.identity, role, privilege.lower(), grant_option=option)
                for role, privilege, option in program.access.grants(program.owner)
            ),
        )
    )
