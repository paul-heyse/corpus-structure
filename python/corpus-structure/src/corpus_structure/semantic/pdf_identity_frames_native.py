"""Ordered immutable PDF record frames shared by digest and published proof."""

from pglast import ast
from pglast.stream import RawStream
from sqlalchemy import (
    BigInteger,
    Boolean,
    MetaData,
    Text,
    and_,
    case,
    cast,
    column,
    func,
    literal,
    literal_column,
    or_,
    select,
    true,
    tuple_,
    union,
    union_all,
)
from sqlalchemy.dialects.postgresql import ARRAY, BYTEA, JSONB, array

from .native_program import (
    Assign,
    ForQuery,
    If,
    Local,
    Perform,
    Raise,
    ReturnNext,
    SelectInto,
    column_type,
    core_relation_row,
    core_variable,
    pg_type,
)
from .pdf_payloads import FAMILY
from .pdf_record_digest_native import _placed, _private_function, _row_value, _utf8
from .pdf_record_identity import MAX_FRAME_BYTES, PROTOCOL, RECORD_PROFILE


def _scalar(kind, value):
    return func.ops.pdf_identity_scalar(kind, _utf8(value), type_=BYTEA())


def _array(values, type_):
    return cast(array(values), ARRAY(type_))


def _ordered_frames(model, product, revision):
    companion = model.tables["kb.pdf_record_companion"]
    endpoint = model.tables["kb.pdf_record_endpoint"]
    member = model.tables["kb.pdf_record_membership"]
    node = model.tables["kb.pdf_record_native"]
    field = model.tables["kb.pdf_record_companion_field"]
    present = (
        select(field.c.local_id)
        .where(
            *_placed(field, product, revision),
            field.c.family == "relation",
        )
        .distinct()
        .subquery("field_rows")
    )

    def empty_record(table):
        datatype = pg_type(str(table.schema), table.name)
        return literal_column(
            RawStream()(ast.TypeCast(arg=ast.A_Const(isnull=True), typeName=datatype))
        )

    def identity_row(family, key, *, record=None, member_key=None, fields=None):
        encoded = [
            table.table_valued() if record is table else empty_record(table)
            for table in (companion, endpoint, member, node)
        ]
        family = literal(family) if isinstance(family, str) else family
        key = literal(key) if isinstance(key, str) else key
        return select(
            family.label("family"),
            key.label("key"),
            *(
                value.label(name)
                for value, name in zip(
                    encoded, ("companion", "endpoint", "member", "node"), strict=True
                )
            ),
            (cast(literal(None), BYTEA()) if member_key is None else member_key).label(
                "member_key"
            ),
            (literal(False) if fields is None else fields).label("has_relation_fields"),
        )

    ascii_key = func.ops.pdf_identity_ascii_string
    stream_key = (
        select(
            case(
                (member.c.member_key.is_not(None), func.ops.pdf_identity_text(member.c.member_key)),
                else_=func.ops.pdf_identity_stream_scalar(
                    product, revision, member.c.member_key_stream_id
                ),
            ).label("scalar")
        )
        .correlate(member)
        .offset(0)
        .lateral("member_key")
    )
    text_key = (
        literal("[")
        .op("||")(ascii_key(endpoint.c.relation_id))
        .op("||")(",")
        .op("||")(cast(endpoint.c.ordinal, Text()))
        .op("||")("]")
    )
    member_key = (
        literal("[")
        .op("||")(ascii_key(member.c.parent_id))
        .op("||")(",")
        .op("||")(ascii_key(member.c.field_name))
        .op("||")(",")
        .op("||")(
            func.coalesce(
                ascii_key(func.encode(stream_key.c.scalar, "hex")), cast(member.c.ordinal, Text())
            )
        )
        .op("||")("]")
    )
    rows = union_all(
        identity_row(
            literal("companion/").op("||")(companion.c.family),
            companion.c.local_id,
            record=companion,
            fields=present.c.local_id.is_not(None),
        )
        .select_from(
            companion.outerjoin(
                present,
                and_(companion.c.family == "relation", present.c.local_id == companion.c.local_id),
            )
        )
        .where(*_placed(companion, product, revision)),
        identity_row("document", "root"),
        identity_row("endpoint", text_key, record=endpoint).where(
            *_placed(endpoint, product, revision)
        ),
        identity_row("membership", member_key, record=member, member_key=stream_key.c.scalar)
        .select_from(member.join(stream_key, true()))
        .where(*_placed(member, product, revision)),
        identity_row("native", node.c.record_id, record=node).where(
            *_placed(node, product, revision)
        ),
        identity_row("publication", "root"),
    ).subquery("ordered")
    return select(rows).order_by(rows.c.family.collate("C"), rows.c.key.collate("C"))


def pdf_identity_frame_declarations(model: MetaData) -> tuple[str, str]:
    header = model.tables["ops.pdf_record_document"]
    nodes = model.tables["kb.pdf_record_native"]
    members = model.tables["kb.pdf_record_membership"]
    companions = model.tables["kb.pdf_record_companion"]
    endpoints = model.tables["kb.pdf_record_endpoint"]
    build = model.tables["ops.pdf_stage_build"]
    frozen = model.tables["ops.pdf_frozen_build"]
    params = (
        ("p_product", column_type(header.c.product_id)),
        ("p_revision", column_type(header.c.revision_id)),
        ("p_fold", pg_type("bool")),
    )
    product = core_variable("p_product", header.c.product_id.type)
    revision = core_variable("p_revision", header.c.revision_id.type)
    fold = core_variable("p_fold", Boolean())
    family = core_variable("row_", Text(), "family")
    key = core_variable("row_", Text(), "key")
    field = core_variable("field_", Text())
    descriptor = core_variable("descriptor_", JSONB())
    body = core_variable("body_", JSONB())
    names = core_variable("names_", ARRAY(Text()))
    values = core_variable("values_", ARRAY(BYTEA()))
    frame = core_variable("frame_", BYTEA())
    state = core_variable("state_", BYTEA())
    count = core_variable("count_", BigInteger())
    length = core_variable("length_", BigInteger())
    schema_digest = _row_value("header_", header, "native_schema_digest")

    def values_array(*items):
        return _array(items, BYTEA())

    def fields(*items):
        return Assign("names_", _array(tuple(name for name, _ in items), Text())), Assign(
            "values_", values_array(*(value for _, value in items))
        )

    def append(name, value):
        return (
            Assign("names_", func.array_append(names, name)),
            Assign("values_", func.array_append(values, value)),
        )

    def out(name):
        return core_variable("row_", Text(), name)

    def stream(stream_id):
        return func.ops.pdf_identity_stream_scalar(product, revision, stream_id, type_=BYTEA())

    def string(value):
        return _scalar("s", value)

    def integer(value):
        return _scalar("i", cast(value, Text()))

    def match(name, steps):
        return If(family == name, steps)

    def made_frame(group, identity, labels, values):
        return func.ops.pdf_identity_record_frame(
            schema_digest, group, identity, labels, values, type_=BYTEA()
        )

    publication = (
        Assign("names_", _array(("kind", "recipe_digest"), Text())),
        SelectInto(
            select(values_array(string(frozen.c.kind), string(build.c.recipe_digest)))
            .select_from(frozen.join(build, build.c.build_id == frozen.c.build_id))
            .where(frozen.c.build_id == product),
            ("values_",),
            strict=True,
        ),
    )
    document = fields(
        *(
            (name, string(_row_value("header_", header, name)))
            for name in ("mapping_profile", "contract_version", "native_schema_digest", "root_id")
        )
    )
    scalars = _row_value("node_", nodes, "scalars_json")
    structure = _row_value("node_", nodes, "structure_json")
    scalar_keys = (
        func.jsonb_object_keys(scalars).table_valued(column("key", Text())).render_derived()
    )
    structure_keys = (
        func.jsonb_object_keys(structure["fields"])
        .table_valued(column("key", Text()))
        .render_derived()
    )
    keys = union(select(scalar_keys.c.key), select(structure_keys.c.key)).subquery("keys")
    kind = descriptor["kind"].astext
    native = (
        Assign("node_", out("node")),
        *fields(
            *(
                (name, string(_row_value("node_", nodes, name)))
                for name in ("native_type", "family")
            )
        ),
        ForQuery(
            ("field_",),
            select(keys.c.key).order_by(keys.c.key.collate("C")),
            (
                If(
                    scalars.has_key(field),
                    append(field.op("||")("/value"), func.ops.pdf_identity_inline(scalars[field])),
                    (
                        Assign("descriptor_", structure["fields"][field]),
                        If(
                            kind == "parts",
                            append(
                                field.op("||")("/value"), stream(descriptor["stream_id"].astext)
                            ),
                            (
                                *append(field.op("||")("/kind"), string(kind)),
                                If(
                                    kind == "object",
                                    append(
                                        field.op("||")("/target"),
                                        string(descriptor["target"].astext),
                                    ),
                                    append(
                                        field.op("||")("/length"),
                                        _scalar("i", descriptor["length"].astext),
                                    ),
                                ),
                            ),
                        ),
                    ),
                ),
            ),
        ),
        If(
            structure.has_key("extensions"),
            append("@extensions", stream(structure["extensions"]["stream_id"].astext)),
        ),
    )
    member_key, member_stream, member_kind = (
        _row_value("member_", members, name)
        for name in ("member_key", "member_key_stream_id", "value_kind")
    )
    membership = (
        Assign("member_", out("member")),
        *fields(
            *(
                (name, string(_row_value("member_", members, name)))
                for name in ("parent_id", "field_name")
            )
        ),
        If(
            or_(member_key.is_not(None), member_stream.is_not(None)),
            append("member_key", core_variable("row_", BYTEA(), "member_key")),
            append("ordinal", integer(_row_value("member_", members, "ordinal"))),
        ),
        If(
            member_kind == "record",
            append("target", string(_row_value("member_", members, "record_id"))),
            append(
                "value",
                case(
                    (
                        member_kind == "scalar",
                        func.ops.pdf_identity_inline(_row_value("member_", members, "scalar_json")),
                    ),
                    else_=stream(_row_value("member_", members, "stream_id")),
                ),
            ),
        ),
    )
    companion_family, local_id, companion_body, companion_ordinal = (
        _row_value("companion_", companions, name)
        for name in ("family", "local_id", "body", "ordinal")
    )
    metadata = companion_family == "native_metadata"
    companion = (
        Assign("companion_", out("companion")),
        Assign(
            "body_",
            case(
                (
                    and_(metadata, companion_body["kind"].astext == FAMILY),
                    companion_body.op("-")(
                        _array(("value", "payload_codec", "payload_schema_digest"), Text())
                    ),
                ),
                (metadata, companion_body.op("-")("value")),
                (companion_family == "occurrence", companion_body.op("-")("text")),
                (
                    core_variable("row_", Boolean(), "has_relation_fields"),
                    func.ops.pdf_companion_restore_fields(
                        product,
                        revision,
                        companion_family,
                        local_id,
                        companion_body,
                    ),
                ),
                else_=companion_body,
            ),
        ),
        If(
            companion_family == "input",
            (
                Assign(
                    "body_",
                    func.jsonb_build_object(
                        "role",
                        companion_body["role"],
                        "target_meaning",
                        func.ops.pdf_identity_published_target(
                            cast(companion_body["task_id"].astext, BigInteger()),
                            companion_body["product_key"].astext,
                            companion_body["content_digest"].astext,
                        ),
                    ),
                ),
            ),
        ),
        *fields(
            ("body", func.ops.pdf_identity_text(func.data.canonical_json(body))),
            ("ordinal", integer(companion_ordinal)),
        ),
        If(
            family.in_(("companion/native_metadata", "companion/occurrence")),
            (
                Assign(
                    "field_", case((family == "companion/native_metadata", "value"), else_="text")
                ),
                *append(
                    field,
                    func.ops.pdf_identity_companion_scalar(
                        product,
                        revision,
                        companion_family,
                        local_id,
                        field,
                        companion_body,
                    ),
                ),
            ),
        ),
    )
    end_task, end_key, end_digest = (
        _row_value("endpoint_", endpoints, name)
        for name in ("target_task_id", "target_product_key", "target_content_digest")
    )
    endpoint = (
        Assign("endpoint_", out("endpoint")),
        If(
            and_(
                end_task == 0,
                tuple_(end_key, end_digest).is_distinct_from(tuple_("@self", "@self")),
            ),
            (Raise("logical PDF self endpoint differs from canonical physical sentinel", "23514"),),
        ),
        *fields(
            (
                "relation_id",
                func.ops.pdf_identity_text(_row_value("endpoint_", endpoints, "relation_id")),
            ),
            ("ordinal", integer(_row_value("endpoint_", endpoints, "ordinal"))),
            (
                "target_meaning",
                func.ops.pdf_identity_text(
                    case(
                        (end_task == 0, "@self"),
                        else_=func.data.canonical_json(
                            func.ops.pdf_identity_published_target(end_task, end_key, end_digest)
                        ),
                    )
                ),
            ),
            *(
                (name, func.ops.pdf_identity_text(_row_value("endpoint_", endpoints, name)))
                for name in ("occurrence_id", "role")
            ),
        ),
    )
    fold_frame = Assign("state_", func.ops.pdf_identity_fold_step(state, count, frame))
    count_frame = (
        Assign("count_", count + 1),
        Assign("length_", length + func.octet_length(frame)),
    )
    return _private_function(
        "pdf_record_identity_frames",
        params,
        "bytea",
        (
            SelectInto(
                select(core_relation_row(header))
                .select_from(header)
                .where(*_placed(header, product, revision)),
                ("header_",),
                strict=True,
            ),
            Perform(
                func.ops.pdf_contract_input(
                    _row_value("header_", header, "release_id"),
                    "implementation/pdf/staging-model.yaml",
                )
            ),
            Assign(
                "frame_",
                made_frame(
                    "@context",
                    "@context",
                    _array(("protocol", "record_profile", "source"), Text()),
                    values_array(
                        string(PROTOCOL),
                        string(RECORD_PROFILE),
                        string(_row_value("header_", header, "source_digest")),
                    ),
                ),
            ),
            If(fold, (fold_frame,), (ReturnNext(frame),)),
            *count_frame,
            ForQuery(
                ("row_",),
                _ordered_frames(model, product, revision),
                (
                    *fields(),
                    match("publication", publication),
                    match("document", document),
                    match("native", native),
                    match("membership", membership),
                    If(func.left(family, 10) == "companion/", companion),
                    match("endpoint", endpoint),
                    Assign("frame_", made_frame(family, key, names, values)),
                    If(
                        fold,
                        (fold_frame,),
                        (
                            If(
                                or_(
                                    func.octet_length(frame) > MAX_FRAME_BYTES,
                                    count >= 1_000_000,
                                    length + func.octet_length(frame) > 384 * 1024**2,
                                ),
                                (Raise("review native proof exceeds frame budget", "54000"),),
                            ),
                            ReturnNext(frame),
                        ),
                    ),
                    *count_frame,
                ),
            ),
            If(fold, (ReturnNext(func.ops.pdf_identity_fold_finish(state, count, length)),)),
        ),
        (
            Local("header_", header),
            Local("row_", pg_type("record")),
            Local("node_", nodes),
            Local("member_", members),
            Local("companion_", companions),
            Local("endpoint_", endpoints),
            Local("field_", pg_type("text")),
            Local("descriptor_", pg_type("jsonb")),
            Local("body_", pg_type("jsonb")),
            Local("names_", _array_type("text")),
            Local("values_", _array_type("bytea")),
            Local("frame_", pg_type("bytea")),
            Local("state_", pg_type("bytea"), func.ops.pdf_identity_fold_start("records")),
            Local("count_", pg_type("int8"), literal(0)),
            Local("length_", pg_type("int8"), literal(0)),
        ),
        setof=True,
    )


def _array_type(datatype):
    result = pg_type(datatype)
    result.arrayBounds = (ast.Integer(ival=-1),)
    return result
