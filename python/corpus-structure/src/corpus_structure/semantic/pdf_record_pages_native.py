"""Model-owned keyset pages for published records and frozen callbacks."""

from dataclasses import dataclass

from pglast import ast
from pglast.stream import RawStream
from sqlalchemy import (
    Integer,
    MetaData,
    Table,
    Text,
    and_,
    any_,
    case,
    cast,
    column,
    func,
    literal,
    or_,
    select,
    tuple_,
)
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, aggregate_order_by, array

from .native_objects import NativeIdentity, native_privilege_sql, native_sql_script
from .native_program import (
    Assign,
    Block,
    If,
    Local,
    Parameter,
    Raise,
    Return,
    ReturnQuery,
    SelectInto,
    column_type,
    core_relation_row,
    core_variable,
    function,
    pg_type,
)
from .native_program import literal as pg_literal
from .pdf_record_model import artifact_part_upload_table


@dataclass(frozen=True)
class RecordPageFamily:
    name: str
    relation: str
    key: tuple[str, ...]
    filters: tuple[str, ...] = ()
    body_filters: tuple[str, ...] = ()
    has_stream_set: bool = False


_FAMILIES = (
    RecordPageFamily("header", "ops.pdf_record_document", ("product_id",)),
    RecordPageFamily(
        "native", "kb.pdf_record_native", ("record_id",), ("record_id", "native_address")
    ),
    RecordPageFamily(
        "membership",
        "kb.pdf_record_membership",
        ("parent_id", "field_name", "ordinal"),
        ("parent_id", "field_name"),
    ),
    RecordPageFamily(
        "reference", "kb.pdf_record_reference", ("reference_id",), ("source_id", "target_id")
    ),
    RecordPageFamily(
        "artifact_stream",
        "ops.pdf_artifact_stream",
        ("stream_id",),
        ("stream_id",),
        has_stream_set=True,
    ),
    RecordPageFamily(
        "artifact_part",
        "ops.pdf_shared_stream_part",
        ("stream_id", "ordinal"),
        ("stream_id",),
        has_stream_set=True,
    ),
    RecordPageFamily(
        "companion",
        "kb.pdf_record_companion",
        ("family", "ordinal", "local_id"),
        ("family", "local_id"),
        ("kind", "pointer", "page_nos"),
    ),
    RecordPageFamily(
        "companion_field",
        "kb.pdf_record_companion_field",
        ("family", "local_id", "field_name"),
        ("family", "local_id", "field_name"),
    ),
    RecordPageFamily(
        "endpoint",
        "kb.pdf_record_endpoint",
        ("relation_id", "ordinal"),
        ("relation_id", "occurrence_id"),
    ),
)


def _json(value: str):
    return cast(literal(value), JSONB())


def _companion_fields(model, row):
    fields = model.tables["kb.pdf_record_companion_field"]
    streams = model.tables["ops.pdf_artifact_stream"]
    attachment = func.jsonb_build_object(
        "field_name",
        fields.c.field_name,
        "stream_id",
        fields.c.stream_id,
        "scalar_kind",
        fields.c.scalar_kind,
        "encoding_profile",
        streams.c.encoding_profile,
    )
    return func.coalesce(
        select(func.jsonb_agg(aggregate_order_by(attachment, fields.c.field_name)))
        .select_from(
            fields.join(
                streams,
                and_(
                    *(
                        fields.c[name] == streams.c[name]
                        for name in ("product_id", "revision_id", "stream_id")
                    )
                ),
            )
        )
        .where(
            *(
                fields.c[name] == row.c[name]
                for name in ("product_id", "revision_id", "family", "local_id")
            )
        )
        .correlate(row)
        .scalar_subquery(),
        _json("[]"),
    )


def _page(model: MetaData, spec: RecordPageFamily, build, filters, after, limit, stream_ids):
    if spec.name == "artifact_part":
        shape = artifact_part_upload_table(model)
        row = func.ops.pdf_artifact_parts(build, build, False, stream_ids).table_valued(
            *(column(field.name, field.type) for field in shape.c)
        )
    else:
        row = model.tables[spec.relation].alias("r")
    keys = tuple(row.c[name] for name in spec.key)
    bound = tuple(cast(after[i].astext, field.type) for i, field in enumerate(keys))
    seek = tuple_(*keys) > tuple_(*bound)
    output = func.to_jsonb(row.table_valued(), type_=JSONB()).op("||")(
        func.jsonb_build_object("_cursor", func.jsonb_build_array(*keys))
    )
    conditions = [
        or_(~filters.has_key(name), row.c[name] == filters[name].astext) for name in spec.filters
    ]
    if spec.has_stream_set:
        ids = func.jsonb_array_elements_text(filters["stream_ids"]).table_valued(
            column("value", Text())
        )
        conditions.append(
            or_(~filters.has_key("stream_ids"), row.c.stream_id.in_(select(ids.c.value)))
        )
    if spec.body_filters:
        pages = func.jsonb_array_elements(filters["page_nos"]).table_valued(
            column("value", JSONB())
        )
        conditions.extend(
            (
                or_(~filters.has_key("kind"), row.c.body["kind"] == filters["kind"]),
                or_(~filters.has_key("pointer"), row.c.body["pointer"] == filters["pointer"]),
                or_(~filters.has_key("page_nos"), row.c.body["page_no"].in_(select(pages.c.value))),
            )
        )
        seek = or_(
            and_(
                after[1] == _json("null"),
                or_(
                    row.c.family > bound[0],
                    and_(
                        row.c.family == bound[0], row.c.ordinal.is_(None), row.c.local_id > bound[2]
                    ),
                ),
            ),
            and_(
                after[1] != _json("null"),
                or_(seek, and_(row.c.family == bound[0], row.c.ordinal.is_(None))),
            ),
        )
        output = output.op("||")(func.jsonb_build_object("_fields", _companion_fields(model, row)))
    return (
        select(output)
        .select_from(row)
        .where(
            row.c.product_id == build,
            row.c.revision_id == build,
            *conditions,
            or_(after.is_(None), seek),
        )
        .order_by(
            *(
                field.nulls_last() if name == "ordinal" else field
                for name, field in zip(spec.key, keys, strict=True)
            )
        )
        .limit(limit)
    )


def pdf_record_page_sql(model: MetaData, *, frozen: bool = False) -> str:
    """Read the same immutable record placement after acquiring the applicable pin."""
    placement = model.tables["ops.pdf_stage_build" if frozen else "ops.pdf_published_revision"]
    task = core_variable("p_task", placement.c.task_id.type)
    build = core_variable("published", placement.c.build_id.type, "build_id")
    family = core_variable("p_family", Text())
    filters = core_variable("p_filters", JSONB())
    after = core_variable("p_after", JSONB())
    limit = core_variable("p_limit", Integer())
    stream_ids = core_variable("selected_stream_ids", ARRAY(Text()))
    filter_names = (
        func.jsonb_object_keys(filters).table_valued(column("value", Text())).render_derived()
    )
    stream_values = func.jsonb_array_elements(filters["stream_ids"]).table_valued(
        column("value", JSONB())
    )
    stream_text = func.jsonb_array_elements_text(filters["stream_ids"]).table_valued(
        column("value", Text())
    )
    invalid_set = Raise("published stream set requires 1..512 exact IDs", "22023")

    task_parameter = Parameter("p_task", column_type(placement.c.task_id))
    filter_parameter = Parameter("p_filters", pg_type("jsonb"))
    after_parameter = Parameter("p_after", pg_type("jsonb"))
    limit_parameter = Parameter("p_limit", pg_type("int4"))
    family_parameter = Parameter("p_family", pg_type("text"))
    if frozen:
        snapshot = model.tables["ops.pdf_frozen_build"]
        fields = (
            ("p_build", placement.c.build_id),
            ("p_attempt", placement.c.attempt),
            ("p_holder", placement.c.holder),
            ("p_frozen", snapshot.c.frozen_digest),
        )
        pins = {name: core_variable(name, field.type) for name, field in fields}
        p_build, attempt, holder, digest = (
            Parameter(name, column_type(field)) for name, field in fields
        )
        parameters = (
            p_build,
            task_parameter,
            attempt,
            holder,
            digest,
            family_parameter,
            after_parameter,
            limit_parameter,
            Parameter(
                "p_filters",
                pg_type("jsonb"),
                ast.TypeCast(arg=pg_literal("{}"), typeName=pg_type("jsonb")),
            ),
        )
        acquire = Assign(
            "published",
            func.ops.require_pdf_frozen(
                pins["p_build"], task, pins["p_attempt"], pins["p_holder"], pins["p_frozen"]
            ),
        )
        name = "read_pdf_frozen_rows"
        roles = ("corpus_sem_writer",)
    else:
        parameters = (
            task_parameter,
            Parameter("p_product", column_type(placement.c.product_key)),
            Parameter("p_digest", column_type(placement.c.logical_digest)),
            family_parameter,
            filter_parameter,
            after_parameter,
            limit_parameter,
        )
        rows = func.ops.read_pdf_published_revision(
            task,
            core_variable("p_product", placement.c.product_key.type),
            core_variable("p_digest", placement.c.logical_digest.type),
        ).table_valued(*(column(field.name, field.type) for field in placement.c))
        # The function returns its installed composite. Expanding its fields in server
        # order keeps SELECT INTO independent of metadata declaration order.
        acquire = SelectInto(
            select(core_relation_row(Table("placement", MetaData()))).select_from(
                rows.alias("placement")
            ),
            ("published",),
            strict=True,
        )
        name = "read_pdf_record_rows"
        roles = ("corpus_sem_reader", "corpus_sem_writer", "corpus_sem_evaluator")

    branches = []
    for spec in _FAMILIES:
        names = spec.filters + spec.body_filters + (("stream_ids",) if spec.has_stream_set else ())
        steps: list[If | Assign] = [
            If(
                select(1)
                .select_from(filter_names)
                .where(~(filter_names.c.value == any_(array(names, type_=Text()))))
                .exists(),
                (Raise("unsupported published record filter", "22023"),),
            )
        ]
        if spec.has_stream_set:
            steps.extend(
                (
                    If(
                        filters.has_key("stream_ids"),
                        (
                            If(
                                func.jsonb_typeof(filters["stream_ids"]).is_distinct_from("array"),
                                (invalid_set,),
                            ),
                            If(
                                or_(
                                    ~func.jsonb_array_length(filters["stream_ids"]).between(1, 512),
                                    select(1)
                                    .select_from(stream_values)
                                    .where(func.jsonb_typeof(stream_values.c.value) != "string")
                                    .exists(),
                                ),
                                (invalid_set,),
                            ),
                        ),
                    ),
                    Assign(
                        "selected_stream_ids",
                        case(
                            (
                                filters.has_key("stream_id"),
                                array([filters["stream_id"].astext], type_=Text()),
                            ),
                            (
                                filters.has_key("stream_ids"),
                                select(func.array_agg(stream_text.c.value)).scalar_subquery(),
                            ),
                        ),
                    ),
                )
            )
        branches.append(
            If(
                family == spec.name,
                (
                    *steps,
                    ReturnQuery(_page(model, spec, build, filters, after, limit, stream_ids)),
                    Return(),
                ),
            )
        )
    result = pg_type("jsonb")
    result.setof = True
    text_array = pg_type("text")
    text_array.arrayBounds = (ast.Integer(ival=-1),)
    definition = function(
        "ops",
        name,
        parameters=parameters,
        returns=result,
        security_definer=True,
        search_path=("pg_catalog", "pg_temp"),
        body=Block(
            (
                If(
                    or_(
                        limit.is_(None),
                        ~limit.between(1, 1000),
                        filters.is_(None),
                        func.jsonb_typeof(filters) != "object",
                        and_(after.is_not(None), func.jsonb_typeof(after) != "array"),
                    ),
                    (Raise("invalid published record page", "22023"),),
                ),
                acquire,
                *branches,
                Raise("unknown published record family", "22023"),
            ),
            (Local("published", placement), Local("selected_stream_ids", text_array)),
        ),
    )
    identity = NativeIdentity(
        "function", "ops", name, tuple(RawStream()(item.type_) for item in parameters)
    )
    return (
        native_sql_script(
            (
                definition,
                native_privilege_sql(identity, "PUBLIC", grant=False),
                *(native_privilege_sql(identity, role, "execute") for role in roles),
            )
        )
        + "\n"
    )
