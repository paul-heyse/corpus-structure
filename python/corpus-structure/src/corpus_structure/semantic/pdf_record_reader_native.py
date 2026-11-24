"""Published-only bounded record access, composed into forward native authoring."""

from sqlalchemy import (
    BigInteger,
    MetaData,
    Numeric,
    Table,
    Text,
    cast,
    column,
    func,
    or_,
    select,
    true,
    union_all,
)
from sqlalchemy.dialects.postgresql import JSONB

from corpus_structure.schema.integrity import role_name

from .metadata import get_metadata
from .native_objects import NativeProgramAccess, native_privilege_sql, native_sql_script
from .native_program import (
    Block,
    If,
    Local,
    NativeRoutine,
    Parameter,
    Raise,
    Return,
    SelectInto,
    column_type,
    core_relation_row,
    core_variable,
    pg_type,
)
from .native_program_registry import ProgramDeclaration
from .pdf_record_event_queries import (
    companion_event_query,
    companion_event_relation,
)
from .pdf_record_pages_native import pdf_record_page_programs, pdf_record_page_sql


def pdf_record_reader_sql(*, target_metadata: MetaData | None = None) -> str:
    model = get_metadata() if target_metadata is None else target_metadata
    return pdf_record_page_sql(model) + pdf_materialization_bound_sql(model)


def pdf_record_reader_programs(
    *, target_metadata: MetaData | None = None
) -> tuple[ProgramDeclaration, ...]:
    model = get_metadata() if target_metadata is None else target_metadata
    return (*pdf_record_page_programs(model), *pdf_materialization_bound_programs(model))


def _reader_program(routine: NativeRoutine) -> ProgramDeclaration:
    return ProgramDeclaration(
        routine,
        "target-current:PDF publication",
        role_name("publisher"),
        NativeProgramAccess(purposes=("read", "write", "evaluate")),
    )


def _reader_sql(item: ProgramDeclaration) -> str:
    return (
        native_sql_script(
            (
                item.render(),
                native_privilege_sql(item.identity, "PUBLIC", grant=False),
                *(
                    native_privilege_sql(item.identity, role, "execute")
                    for role in (role_name("reader"), role_name("writer"), role_name("evaluator"))
                ),
            )
        )
        + "\n"
    )


def _export_program(model, name, product_parameter, query_builder, *, family=False):
    placement = model.tables["ops.pdf_published_revision"]
    fields = (
        ("p_task", placement.c.task_id),
        (product_parameter, placement.c.product_key),
        ("p_digest", placement.c.logical_digest),
    )
    parameters = tuple(Parameter(label, column_type(source)) for label, source in fields)
    pin = (core_variable(label, source.type) for label, source in fields)
    publication = func.ops.read_pdf_published_revision(*pin).table_valued(
        column("build_id", placement.c.build_id.type)
    )
    published = select(publication.c.build_id).cte("published").prefix_with("MATERIALIZED")
    if family:
        parameters += (Parameter("p_family", pg_type("text")),)
    returns = pg_type("record")
    returns.setof = True
    query = query_builder(model, published)
    definition = NativeRoutine(
        "ops",
        name,
        parameters=parameters,
        returns=returns,
        table_columns=(("body", pg_type("jsonb")), ("part_body", pg_type("bytea"))),
        body=query,
        security_definer=True,
        search_path=("pg_catalog", "pg_temp"),
        volatility="stable",
    )
    return _reader_program(definition)


def pdf_companion_export_programs(
    *, target_metadata: MetaData | None = None
) -> tuple[ProgramDeclaration, ...]:
    """Read an exact companion, field and part cursor for a published product."""

    def query(model, published):
        rows = model.tables["kb.pdf_record_companion"]
        family = core_variable("p_family", rows.c.family.type)
        companions = (
            select(rows)
            .select_from(
                rows.join(
                    published,
                    (rows.c.product_id == published.c.build_id)
                    & (rows.c.revision_id == published.c.build_id),
                )
            )
            .where(rows.c.family == family)
            .subquery("requested_companions")
        )
        return companion_event_query(companion_event_relation(model, companions))

    model = get_metadata() if target_metadata is None else target_metadata
    return (
        _export_program(model, "read_pdf_companion_export_events", "p_key", query, family=True),
    )


def pdf_materialization_bound_programs(model: MetaData) -> tuple[ProgramDeclaration, ...]:
    """Conservatively bound native and companion encoded inputs before transfer."""
    placement = model.tables["ops.pdf_published_revision"]
    task, product, digest = (
        core_variable(name, field.type)
        for name, field in (
            ("p_task", placement.c.task_id),
            ("p_product", placement.c.product_key),
            ("p_digest", placement.c.logical_digest),
        )
    )
    build = core_variable("published", placement.c.build_id.type, "build_id")
    rows = (
        func.ops.read_pdf_published_revision(task, product, digest)
        .table_valued(*(column(field.name, field.type) for field in placement.c))
        .alias("placement")
    )
    read_placement = SelectInto(
        select(core_relation_row(Table("placement", MetaData()))).select_from(rows),
        ("published",),
        strict=True,
    )

    def byte_count(value):
        return func.coalesce(func.sum(cast(value, Numeric())), 0)

    def placed(row):
        return row.c.product_id == build, row.c.revision_id == build

    artifacts = model.tables["kb.source_artifact"]
    streams = model.tables["ops.pdf_artifact_stream"]
    natives = model.tables["kb.pdf_record_native"]
    membership = model.tables["kb.pdf_record_membership"]
    fields = (
        func.jsonb_each(natives.c.structure_json["fields"])
        .table_valued(column("key", Text()), column("value", JSONB()))
        .lateral("descriptor")
    )
    native_stream_uses = union_all(
        select(fields.c.value["stream_id"].astext.label("stream_id"))
        .select_from(natives.join(fields, true()))
        .where(*placed(natives), fields.c.value["kind"].astext == "parts"),
        select(natives.c.structure_json["extensions"]["stream_id"].astext).where(
            *placed(natives), natives.c.structure_json.has_key("extensions")
        ),
        select(membership.c.stream_id).where(
            *placed(membership), membership.c.stream_id.is_not(None)
        ),
        select(membership.c.member_key_stream_id).where(
            *placed(membership), membership.c.member_key_stream_id.is_not(None)
        ),
    ).subquery("native_stream_uses")
    native_bytes = (
        select(byte_count(streams.c.byte_length))
        .select_from(
            native_stream_uses.join(streams, streams.c.stream_id == native_stream_uses.c.stream_id)
        )
        .where(*placed(streams))
    )
    # The aggregate includes the acquired bytes of all streams as well as each
    # native use expanded in a document. This covers shared streams without a
    # containment walk or transfer of the stored part bodies.
    acquired_stream_bytes = select(byte_count(streams.c.byte_length)).where(*placed(streams))
    record_bytes = []
    for name in (
        "ops.pdf_record_document",
        "kb.pdf_record_native",
        "kb.pdf_record_membership",
        "kb.pdf_record_companion",
        "kb.pdf_record_companion_field",
    ):
        row = model.tables[name]
        size = func.octet_length(cast(func.to_jsonb(row.table_valued()), Text()))
        record_bytes.append(select(byte_count(size)).where(*placed(row)))
    raw_bytes = select(byte_count(func.octet_length(artifacts.c.content))).where(
        artifacts.c.artifact_digest.in_(
            tuple(
                core_variable("published", placement.c[name].type, name)
                for name in ("source_digest", "schema_digest", "recipe_digest")
            )
        )
    )
    # A JSON string may take six encoded bytes per input byte.
    escaped = (
        sum(
            query.scalar_subquery()
            for query in (native_bytes, acquired_stream_bytes, *record_bytes)
        )
        * 6
    )
    total = core_variable("total", Numeric())
    name = "read_pdf_materialization_bound"
    definition = NativeRoutine(
        "ops",
        name,
        parameters=(
            Parameter("p_task", column_type(placement.c.task_id)),
            Parameter("p_product", column_type(placement.c.product_key)),
            Parameter("p_digest", column_type(placement.c.logical_digest)),
        ),
        returns=pg_type("int8"),
        security_definer=True,
        search_path=("pg_catalog", "pg_temp"),
        volatility="stable",
        body=Block(
            (
                read_placement,
                SelectInto(select(escaped + raw_bytes.scalar_subquery()), ("total",)),
                If(
                    or_(total.is_(None), total < 0, total > 2**63 - 1),
                    (Raise("PDF materialization bound exceeds signed integer capacity", "22003"),),
                ),
                Return(cast(total, BigInteger())),
            ),
            (Local("published", placement), Local("total", pg_type("numeric"))),
        ),
    )
    return (_reader_program(definition),)


def pdf_companion_export_sql(*, target_metadata: MetaData | None = None) -> str:
    return _reader_sql(pdf_companion_export_programs(target_metadata=target_metadata)[0])


def pdf_materialization_bound_sql(model: MetaData) -> str:
    return _reader_sql(pdf_materialization_bound_programs(model)[0])
