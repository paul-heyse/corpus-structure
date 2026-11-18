"""Protected companion set adoption from captured models and typed native steps."""

import json

from sqlalchemy import (
    BigInteger,
    Column,
    MetaData,
    Table,
    Text,
    and_,
    case,
    cast,
    column,
    func,
    literal,
    not_,
    or_,
    select,
    true,
    tuple_,
)
from sqlalchemy.dialects.postgresql import JSON, JSONB, REGCLASS, array, insert

from .native_program import (
    Assign,
    Block,
    If,
    Local,
    Parameter,
    Perform,
    PerformQuery,
    Raise,
    SelectInto,
    Sql,
    Statement,
    column_type,
    core_variable,
    function,
    pg_type,
)
from .native_shapes import record_shape_expression
from .pdf_payload_validation import metadata_classes
from .pdf_payloads import FAMILY, PROFILE
from .pdf_shared_streams import pdf_companion_scratch_specs, pdf_scratch_prepare
from .pdf_staging import stage_upload_profile
from .pdf_staging_native import native_payload_size_expression


def companion_adoption_sql(context, metadata):
    specs = pdf_companion_scratch_specs(metadata)
    targets = {spec.source.name: spec.source for spec in specs}
    scratch = {
        name: Table(
            "pc_" + name,
            MetaData(),
            *(Column(field.name, field.type, nullable=field.nullable) for field in relation.c),
            schema="pg_temp",
        )
        for name, relation in targets.items()
    }
    companion, field, stream, part, endpoint = (
        scratch["pdf_stage_" + name]
        for name in ("companion", "companion_field", "artifact_stream", "artifact_part", "endpoint")
    )
    retained = targets["pdf_stage_companion"]
    retained_field = targets["pdf_stage_companion_field"]
    build = metadata.tables["ops.pdf_stage_build"]
    profile = stage_upload_profile(physical_sources=metadata.info["physical_sources"])
    p_build, p_task, p_attempt, p_holder = (
        core_variable(name, col.type)
        for name, col in (
            ("p_build", build.c.build_id),
            ("p_task", build.c.task_id),
            ("p_attempt", build.c.attempt),
            ("p_holder", build.c.holder),
        )
    )
    p_key = core_variable("p_key", Text())
    n, size, total, total_bytes = (
        core_variable(name, BigInteger()) for name in ("n", "size_", "total", "total_bytes")
    )
    body = companion.c.body

    def refuse(query, message):
        return If(query.exists(), (Raise(message, "23514"),))

    def any_row(relation, *predicates):
        return select(1).select_from(relation).where(*predicates)

    def has(value, name):
        return value.bool_op("?")(name)

    def json_value(value):
        return cast(literal(json.dumps(value, ensure_ascii=False, separators=(",", ":"))), JSONB())

    def json_object(*items):
        return func.jsonb_build_object(*items, type_=JSONB())

    def equality_fields(incoming, stored, names):
        return tuple_(*(incoming.c[name] for name in names)).is_distinct_from(
            tuple_(*(stored.c[name] for name in names))
        )

    def adopt(name, message):
        incoming, stored = scratch[name].alias("incoming"), targets[name].alias("retained")
        match = and_(
            *(incoming.c[key.name] == stored.c[key.name] for key in targets[name].primary_key)
        )
        return (
            refuse(
                any_row(
                    incoming.join(stored, match),
                    equality_fields(incoming, stored, targets[name].c.keys()),
                ),
                message,
            ),
            Sql(
                insert(targets[name])
                .from_select(tuple(targets[name].c.keys()), select(*scratch[name].c))
                .on_conflict_do_nothing()
            ),
        )

    statements: list[Statement] = [
        Assign("b", func.ops.require_pdf_build(p_build, p_task, p_attempt, p_holder)),
        Perform(
            func.ops.require_pdf_operation(
                core_variable("b", build.c.release_id.type, "release_id"), "adopt_pdf_companions"
            )
        ),
        If(
            or_(
                p_key.is_(None),
                p_key == "",
                func.octet_length(p_key) > profile["max_replay_key_bytes"],
            ),
            (Raise("invalid companion replay key", "23514"),),
        ),
    ]
    for spec in specs:
        relation = scratch[spec.source.name]
        prototype = (
            func.ops.pdf_part_upload_contract()
            if spec.source.name == "pdf_stage_artifact_part"
            else cast(literal(str(spec.source.fullname)), REGCLASS())
        )
        statements.extend(
            (
                Perform(func.ops.require_pdf_stage_scratch(str(relation.name), prototype)),
                If(
                    or_(
                        any_row(
                            relation,
                            or_(
                                relation.c.product_id.is_distinct_from(p_build),
                                relation.c.revision_id.is_distinct_from(p_build),
                            ),
                        ).exists(),
                        select(1)
                        .select_from(relation)
                        .group_by(*(relation.c[key.name] for key in spec.source.primary_key))
                        .having(func.count() > 1)
                        .exists(),
                    ),
                    (Raise("companion upload ownership or duplicate key differs", "23514"),),
                ),
            )
        )
        if spec.source.name != "pdf_stage_artifact_part":
            statements.extend(
                (
                    SelectInto(
                        select(
                            func.count(),
                            func.coalesce(func.sum(native_payload_size_expression(relation)), 0),
                        ).select_from(relation),
                        ("n", "size_"),
                    ),
                    Assign("total", total + n),
                    Assign("total_bytes", total_bytes + size),
                    If(
                        or_(total > profile["max_rows"], total_bytes > profile["max_native_bytes"]),
                        (Raise("companion upload profile exceeded", "23514"),),
                    ),
                )
            )
    ordinary_identity = (
        ("occurrence", "occurrence_id"),
        ("relation", "relation_id"),
        ("coverage", "coverage_id"),
    )
    invalid_identity = or_(
        companion.c.local_id == "",
        companion.c.ordinal < 0,
        func.jsonb_typeof(body).is_distinct_from("object"),
        func.octet_length(cast(body, Text())) > 65536,
        *(
            and_(
                companion.c.family == family,
                companion.c.local_id.is_distinct_from(body[key].astext),
            )
            for family, key in ordinary_identity
        ),
        and_(
            companion.c.family.in_(("input", "mapping_report")),
            companion.c.local_id.is_distinct_from(cast(companion.c.ordinal, Text())),
        ),
        and_(
            companion.c.family == "native_metadata",
            companion.c.local_id.is_distinct_from(
                body["kind"].astext + ":" + body["ordinal"].astext
            ),
        ),
    )
    incoming_groups = (
        select(1)
        .select_from(companion)
        .group_by(
            companion.c.family,
            case((companion.c.family == "native_metadata", body["kind"].astext), else_=""),
            companion.c.ordinal,
        )
        .having(func.count() > 1)
    )
    old = retained.alias("old")
    conflicting_order = any_row(
        companion.join(
            old,
            and_(
                old.c.product_id == p_build,
                old.c.family == companion.c.family,
                old.c.ordinal == companion.c.ordinal,
                old.c.local_id != companion.c.local_id,
                or_(
                    companion.c.family != "native_metadata",
                    old.c.body["kind"].astext == body["kind"].astext,
                ),
            ),
        )
    )
    statements.extend(
        (
            refuse(any_row(endpoint), "companion endpoints must be derived natively"),
            If(
                or_(
                    any_row(companion, invalid_identity).exists(),
                    incoming_groups.exists(),
                    conflicting_order.exists(),
                ),
                (Raise("companion identity/order differs from declared semantic row", "23514"),),
            ),
        )
    )
    field_keys = ("product_id", "revision_id", "family", "local_id")
    owner_join = and_(*(field.c[name] == companion.c[name] for name in field_keys))
    statements.append(
        refuse(
            any_row(
                field.outerjoin(companion, owner_join),
                or_(
                    companion.c.local_id.is_(None),
                    has(body, field.c.field_name),
                    not_(
                        or_(
                            and_(
                                field.c.family == "native_metadata", field.c.field_name == "value"
                            ),
                            and_(field.c.family == "occurrence", field.c.field_name == "text"),
                            and_(
                                field.c.family == "relation",
                                field.c.field_name.in_(("endpoints", "evidence")),
                            ),
                        )
                    ),
                    field.c.scalar_kind.is_distinct_from(
                        case((field.c.field_name.in_(("value", "endpoints")), "y"), else_="s")
                    ),
                ),
            ),
            "invalid companion external field",
        )
    )
    statements.append(
        If(
            or_(
                *(
                    any_row(
                        relation,
                        ~select(1)
                        .select_from(field)
                        .where(field.c.stream_id == relation.c.stream_id)
                        .correlate(relation)
                        .exists(),
                    ).exists()
                    for relation in (stream, part)
                )
            ),
            (Raise("companion artifact is outside its field inventory", "23514"),),
        )
    )
    statements.extend(
        (
            Perform(
                func.ops.pdf_adopt_shared_stream_descriptors(
                    p_build, cast(literal(str(stream.fullname)), REGCLASS())
                )
            ),
            *adopt("pdf_stage_artifact_stream", "changed companion artifact duplicate"),
            Perform(
                func.ops.pdf_adopt_shared_stream_parts(
                    p_build, cast(literal(str(part.fullname)), REGCLASS())
                )
            ),
            PerformQuery(select(func.ops.pdf_verify_shared_stream(p_build, stream.c.stream_id))),
        )
    )
    stored_stream = targets["pdf_stage_artifact_stream"]
    stream_join = and_(
        stored_stream.c.product_id == p_build,
        stored_stream.c.revision_id == p_build,
        stored_stream.c.stream_id == field.c.stream_id,
    )
    encoding = case(
        (and_(field.c.field_name == "value", body["kind"].astext == FAMILY), PROFILE),
        (field.c.field_name.in_(("value", "endpoints")), "pdf-companion-json-field-v1"),
        else_="pdf-record-scalar-v1:s",
    )
    statements.extend(
        (
            refuse(
                any_row(
                    field.join(companion, owner_join).outerjoin(stored_stream, stream_join),
                    stored_stream.c.encoding_profile.is_distinct_from(encoding),
                ),
                "companion field encoding differs",
            ),
            PerformQuery(
                select(
                    func.sum(
                        func.octet_length(
                            func.ops.pdf_companion_field_bytes(
                                p_build, p_build, field.c.stream_id, True
                            )
                        )
                    )
                )
            ),
        )
    )
    restored = case(
        (
            field.c.field_name == "endpoints",
            cast(
                func.convert_from(
                    func.ops.pdf_companion_field_bytes(p_build, p_build, field.c.stream_id, True),
                    "UTF8",
                ),
                JSONB(),
            ),
        ),
        else_=func.to_jsonb(
            func.convert_from(
                func.ops.pdf_companion_field_bytes(p_build, p_build, field.c.stream_id, True),
                "UTF8",
            ),
            type_=JSONB(),
        ),
    )
    restored_fields = (
        select(func.jsonb_object_agg(field.c.field_name, restored))
        .where(
            field.c.family == companion.c.family,
            field.c.local_id == companion.c.local_id,
            field.c.field_name.in_(("text", "endpoints", "evidence")),
        )
        .correlate(companion)
        .scalar_subquery()
    )
    rows = select(
        *companion.c, body.op("||")(func.coalesce(restored_fields, json_value({}))).label("body_")
    ).cte("rows_")
    for family, cls in (
        ("input", "PdfProductInput"),
        ("occurrence", "PdfProductOccurrence"),
        ("relation", "PdfProductRelation"),
        ("coverage", "PdfProductCoverage"),
        ("mapping_report", "PdfMappingDisposition"),
        ("request_outcome", "PdfRecognitionObservation"),
    ):
        statements.append(
            refuse(
                any_row(
                    rows,
                    rows.c.family == family,
                    record_shape_expression(context.boundary, cls, rows.c.body_),
                ),
                "parsing record shape differs: " + cls,
            )
        )
    for cls, condition in (
        ("PdfRecordNativeHealth", has(body, "conversion")),
        ("PdfProductHealth", not_(has(body, "conversion"))),
    ):
        statements.append(
            refuse(
                any_row(
                    companion,
                    companion.c.family == "health",
                    condition,
                    record_shape_expression(context.boundary, cls, body),
                ),
                "parsing record shape differs: " + cls,
            )
        )
    classes = metadata_classes()
    metadata_keys = case(
        (
            body["kind"].astext == "formula_outcomes",
            array(["kind", "ordinal", "pointer", "outcome", "has_diagnostic"]),
        ),
        (
            body["kind"].astext == FAMILY,
            array(
                [
                    "kind",
                    "ordinal",
                    "pointer",
                    "page_no",
                    "payload_schema_digest",
                    "payload_codec",
                    "payload_logical_digest",
                ]
            ),
        ),
        else_=array(["kind", "ordinal", "pointer"]),
    )
    statements.append(
        refuse(
            any_row(
                companion,
                companion.c.family == "native_metadata",
                or_(
                    body["kind"].astext.not_in(tuple(classes)),
                    body.op("-")(metadata_keys) != json_value({}),
                    func.jsonb_typeof(body["ordinal"]).is_distinct_from("number"),
                    func.coalesce(body["ordinal"].astext, "").bool_op("!~")("^[0-9]+$"),
                    ~select(1)
                    .select_from(field)
                    .where(
                        field.c.family == companion.c.family,
                        field.c.local_id == companion.c.local_id,
                        field.c.field_name == "value",
                    )
                    .correlate(companion)
                    .exists(),
                    and_(
                        body["kind"].astext == "formula_outcomes",
                        or_(
                            func.jsonb_typeof(body["has_diagnostic"]).is_distinct_from("boolean"),
                            func.jsonb_typeof(body["outcome"]).is_distinct_from("string"),
                        ),
                    ),
                    and_(
                        body["kind"].astext == FAMILY,
                        or_(
                            body["payload_codec"].astext.is_distinct_from(PROFILE),
                            func.jsonb_typeof(body["page_no"]).is_distinct_from("number"),
                            func.coalesce(body["page_no"].astext, "").bool_op("!~")(
                                "^[1-9][0-9]*$"
                            ),
                            *(
                                func.coalesce(body[key].astext, "").bool_op("!~")("^[0-9a-f]{64}$")
                                for key in ("payload_schema_digest", "payload_logical_digest")
                            ),
                        ),
                    ),
                ),
            ),
            "invalid metadata envelope",
        )
    )
    properties, alternatives = {}, []
    for property_ in ("pointer", "prose_pointer", "table_pointer"):
        alternatives.append(
            json_object(
                "required",
                func.jsonb_build_array(property_),
                "properties",
                json_value(properties).op("||")(
                    json_object(property_, json_object("type", "string", "const", body["pointer"]))
                ),
            )
        )
        properties[property_] = {"not": {"type": "string"}}
    projection = case(
        (has(body, "pointer"), json_object("anyOf", func.jsonb_build_array(*alternatives))),
        else_=json_value({"properties": properties}),
    )
    formula = case(
        (
            body["kind"].astext == "formula_outcomes",
            json_object(
                "required",
                func.jsonb_build_array("outcome"),
                "properties",
                json_object("outcome", json_object("const", body["outcome"])),
            ).op("||")(
                case(
                    (
                        body["has_diagnostic"] == json_value(True),
                        json_value({"required": ["outcome", "error"]}),
                    ),
                    else_=json_value({"not": {"required": ["error"]}}),
                )
            ),
        ),
        else_=json_value({}),
    )
    for kind, cls in classes.items():
        if kind == FAMILY:
            continue
        from .pdf_publication_native import _schema_json

        schema = cast(literal(_schema_json(context.boundary.json_schema(cls))), JSONB())
        matching = schema.op("||")(
            json_object("allOf", func.jsonb_build_array(projection, formula))
        )
        value = cast(
            func.convert_from(
                func.ops.pdf_companion_field_bytes(p_build, p_build, field.c.stream_id, True),
                "UTF8",
            ),
            JSON(),
        )
        statements.append(
            refuse(
                any_row(
                    companion.join(field, owner_join),
                    companion.c.family == "native_metadata",
                    body["kind"].astext == kind,
                    field.c.field_name == "value",
                    func.public.json_matches_schema(cast(matching, JSON()), value).is_not(True),
                ),
                "metadata value/schema/projection differs: " + cls,
            )
        )
    statements.extend(
        (
            *adopt("pdf_stage_companion", "changed companion duplicate"),
            *adopt("pdf_stage_companion_field", "changed companion field duplicate"),
        )
    )
    count_stored = (
        select(func.count())
        .select_from(retained_field)
        .where(
            retained_field.c.product_id == p_build,
            retained_field.c.family == companion.c.family,
            retained_field.c.local_id == companion.c.local_id,
        )
        .correlate(companion)
        .scalar_subquery()
    )
    count_input = (
        select(func.count())
        .select_from(field)
        .where(
            field.c.family == companion.c.family,
            field.c.local_id == companion.c.local_id,
        )
        .correlate(companion)
        .scalar_subquery()
    )
    statements.append(
        refuse(any_row(companion, count_stored != count_input), "changed companion field inventory")
    )
    incoming = rows.alias("c")
    ends = (
        func.jsonb_array_elements(incoming.c.body_["endpoints"])
        .table_valued(column("value", JSONB()), with_ordinality="ordinality")
        .render_derived()
        .lateral("endpoint")
    )
    input_ = retained.alias("input_")
    has_input = has(ends.c.value, "input_index")
    target_fields = (
        case(
            (has_input, func.coalesce(cast(input_.c.body["task_id"].astext, BigInteger()), 0)),
            else_=0,
        ),
        case(
            (has_input, func.coalesce(input_.c.body["product_key"].astext, "@missing")),
            else_="@self",
        ),
        case(
            (has_input, func.coalesce(input_.c.body["content_digest"].astext, "@missing")),
            else_="@self",
        ),
    )
    endpoint_values = (
        select(
            p_build,
            p_build,
            incoming.c.local_id,
            cast(ends.c.ordinality - 1, BigInteger()),
            *target_fields,
            ends.c.value["occurrence_id"].astext,
            ends.c.value["role"].astext,
        )
        .select_from(
            incoming.join(ends, true()).outerjoin(
                input_,
                and_(
                    input_.c.product_id == p_build,
                    input_.c.family == "input",
                    input_.c.local_id == ends.c.value["input_index"].astext,
                ),
            )
        )
        .where(incoming.c.family == "relation")
    )
    statements.extend(
        (
            Sql(insert(endpoint).from_select(tuple(endpoint.c.keys()), endpoint_values)),
            refuse(
                any_row(endpoint, endpoint.c.target_content_digest == "@missing"),
                "companion endpoint input is outside the admitted input inventory",
            ),
            *adopt("pdf_stage_endpoint", "changed companion endpoint duplicate"),
        )
    )
    parameters = tuple(
        Parameter(name, column_type(col))
        for name, col in (
            ("p_build", build.c.build_id),
            ("p_task", build.c.task_id),
            ("p_attempt", build.c.attempt),
            ("p_holder", build.c.holder),
        )
    )
    return (
        function(
            "ops",
            "prepare_pdf_companions",
            parameters=(),
            returns=pg_type("void"),
            security_definer=True,
            search_path=("pg_catalog", "pg_temp"),
            body=Block(tuple(step for spec in specs for step in pdf_scratch_prepare(spec))),
        )
        + ";\n"
        + function(
            "ops",
            "adopt_pdf_companions",
            parameters=(*parameters, Parameter("p_key", pg_type("text"))),
            returns=pg_type("void"),
            security_definer=True,
            search_path=("pg_catalog", "pg_temp"),
            body=Block(
                tuple(statements),
                (
                    Local("b", build),
                    Local("n", pg_type("bigint")),
                    Local("size_", pg_type("bigint")),
                    Local("total", pg_type("bigint"), literal(0)),
                    Local("total_bytes", pg_type("bigint"), literal(0)),
                ),
            ),
        )
        + ";\n"
    )
