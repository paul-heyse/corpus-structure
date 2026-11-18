"""Published-only bounded record access, composed into forward native authoring."""

from pglast.stream import RawStream
from sqlalchemy import BigInteger, MetaData, Numeric, Table, Text, cast, column, func, or_, select
from sqlalchemy.dialects.postgresql import JSONB

from .metadata import metadata
from .native_objects import NativeIdentity, native_privilege_sql, native_sql_script
from .native_program import (
    Block,
    If,
    Local,
    Parameter,
    Raise,
    Return,
    SelectInto,
    column_type,
    core_relation_row,
    core_variable,
    function,
    pg_type,
    sql_function,
)
from .pdf_record_event_queries import (
    companion_event_query,
    companion_event_relation,
    native_event_query,
    native_event_relations,
)
from .pdf_record_pages_native import pdf_record_page_sql


def pdf_record_reader_sql(*, target_metadata: MetaData | None = None) -> str:
    model = metadata if target_metadata is None else target_metadata
    return pdf_record_page_sql(model) + pdf_materialization_bound_sql(model)


def _export_definition(model, name, product_parameter, query_builder, *, family=False):
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
    returns = pg_type("jsonb")
    returns.setof = True
    query = query_builder(model, published)
    definition = sql_function(
        "ops",
        name,
        parameters=parameters,
        returns=returns,
        body=query,
        security_definer=True,
        search_path=("pg_catalog", "pg_temp"),
        volatility="stable",
    )
    identity = NativeIdentity(
        "function", "ops", name, tuple(RawStream()(parameter.type_) for parameter in parameters)
    )
    return (
        native_sql_script(
            (
                definition,
                native_privilege_sql(identity, "PUBLIC", grant=False),
                *(
                    native_privilege_sql(identity, role, "execute")
                    for role in ("corpus_sem_reader", "corpus_sem_writer", "corpus_sem_evaluator")
                ),
            )
        )
        + "\n"
    )


def pdf_native_export_sql(*, target_metadata: MetaData | None = None) -> str:
    """Read the ordered containment cursor for a published product."""
    model = metadata if target_metadata is None else target_metadata
    return _export_definition(
        model,
        "read_pdf_native_events",
        "p_product",
        lambda model, published: native_event_query(native_event_relations(model, published)),
    )


def pdf_companion_export_sql(*, target_metadata: MetaData | None = None) -> str:
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

    model = metadata if target_metadata is None else target_metadata
    return _export_definition(
        model, "read_pdf_companion_export_events", "p_key", query, family=True
    )


def pdf_materialization_bound_sql(model: MetaData) -> str:
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
    exported = (
        func.ops.read_pdf_native_events(task, product, digest)
        .table_valued(column("event", JSONB()))
        .render_derived()
    )
    events = select(exported.c.event).cte("events").prefix_with("MATERIALIZED")

    def byte_count(value):
        return func.coalesce(func.sum(cast(value, Numeric())), 0)

    def placed(row):
        return row.c.product_id == build, row.c.revision_id == build

    artifacts = model.tables["kb.source_artifact"]
    streams = model.tables["ops.pdf_artifact_stream"]
    event_bytes = select(byte_count(func.octet_length(cast(events.c.event, Text()))))
    # Count repeated native stream uses individually, including escaped JSON strings.
    native_bytes = (
        select(byte_count(streams.c.byte_length))
        .select_from(events.join(streams, streams.c.stream_id == events.c.event["value"].astext))
        .where(
            *placed(streams), events.c.event["kind"].astext.in_(("parts", "key_parts", "extension"))
        )
    )
    companion_stream_bytes = select(byte_count(streams.c.byte_length)).where(*placed(streams))
    record_bytes = []
    for name in ("companion", "companion_field", "membership"):
        row = model.tables[f"kb.pdf_record_{name}"]
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
            for query in (event_bytes, native_bytes, companion_stream_bytes, *record_bytes)
        )
        * 6
    )
    total = core_variable("total", Numeric())
    name = "read_pdf_materialization_bound"
    definition = function(
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
    identity = NativeIdentity("function", "ops", name, ("bigint", "text", "text"))
    return (
        native_sql_script(
            (
                definition,
                native_privilege_sql(identity, "PUBLIC", grant=False),
                *(
                    native_privilege_sql(identity, role, "execute")
                    for role in ("corpus_sem_reader", "corpus_sem_writer", "corpus_sem_evaluator")
                ),
            )
        )
        + "\n"
    )
