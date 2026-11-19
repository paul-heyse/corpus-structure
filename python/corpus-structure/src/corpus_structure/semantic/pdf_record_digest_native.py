"""Canonical PDF record scalar and digest programs."""

from collections.abc import Sequence

from sqlalchemy import (
    BigInteger,
    Boolean,
    Integer,
    MetaData,
    Text,
    and_,
    case,
    cast,
    column,
    func,
    literal,
    or_,
    select,
)
from sqlalchemy.dialects.postgresql import BYTEA, JSONB, aggregate_order_by

from corpus_structure.schema.integrity import role_name

from .native_objects import INTERNAL_PROGRAM, native_privilege_sql, native_sql_script
from .native_program import (
    Block,
    ForQuery,
    If,
    Local,
    NativeRoutine,
    Parameter,
    Perform,
    Raise,
    Return,
    SelectInto,
    Statement,
    column_type,
    core_relation_row,
    core_variable,
    pg_type,
)
from .native_program_registry import ProgramDeclaration
from .pdf_payloads import FAMILY, PROFILE


def _utf8(value):
    return func.convert_to(value, "UTF8", type_=BYTEA())


def _bytes(hexadecimal):
    return func.decode(hexadecimal, "hex", type_=BYTEA())


def _frame(kind, length, digest):
    return _utf8(kind).op("||")(func.int8send(cast(length, BigInteger()))).op("||")(digest)


def _json(value):
    return cast(literal(value), JSONB())


def _placed(row, product, revision):
    return row.c.product_id == product, row.c.revision_id == revision


def _row_value(name, table, field):
    return core_variable(name, table.c[field].type, field)


def _private_program(
    name,
    params,
    kind,
    steps: Sequence[Statement],
    locals_=(),
    *,
    immutable=False,
    strict=False,
    setof=False,
):
    parameters = tuple(Parameter(label, type_) for label, type_ in params)
    result = pg_type(kind)
    result.setof = setof
    routine = NativeRoutine(
        "ops",
        name,
        parameters=parameters,
        returns=result,
        body=Block(tuple(steps), tuple(locals_)),
        search_path=("pg_catalog", "pg_temp"),
        volatility="immutable" if immutable else "stable",
        strict=strict,
    )
    return ProgramDeclaration(
        routine, "authoring/pdf-record-digest.sql", role_name("publisher"), INTERNAL_PROGRAM
    )


def _private_function(
    name,
    params,
    kind,
    steps: Sequence[Statement],
    locals_=(),
    *,
    immutable=False,
    strict=False,
    setof=False,
):
    """Render the shared typed builder for the existing frame/target owners."""
    program = _private_program(
        name, params, kind, steps, locals_, immutable=immutable, strict=strict, setof=setof
    )
    return program.routine.render(), native_privilege_sql(program.identity, "PUBLIC", grant=False)


def _text_identity():
    value = core_variable("p_value", Text())
    payload = core_variable("payload_", BYTEA())
    return _private_program(
        "pdf_identity_text",
        (("p_value", pg_type("text")),),
        "bytea",
        (
            # Non-UTF8 databases still require the byte-level scalar check.
            If(
                func.current_setting("server_encoding") != "UTF8",
                (Return(func.ops.pdf_identity_scalar("s", payload)),),
            ),
            Return(
                _frame("s", func.octet_length(payload), func.ops.pdf_identity_byte_root(payload))
            ),
        ),
        (Local("payload_", pg_type("bytea"), _utf8(value)),),
        immutable=True,
        strict=True,
    )


def _inline_identity():
    value = core_variable("p_value", JSONB())
    kind = core_variable("kind_", Text())
    lexical = value[()].astext
    hexadecimal = value["native_float64"].astext
    keys = func.jsonb_object_keys(value).table_valued("jsonb_object_keys")
    body = (
        If(kind == "null", (Return(func.ops.pdf_identity_scalar("n", _bytes(""))),)),
        If(
            kind == "boolean",
            (
                Return(
                    func.ops.pdf_identity_scalar(
                        "b", _bytes(case((value == _json("true"), "01"), else_="00"))
                    )
                ),
            ),
        ),
        If(kind == "string", (Return(func.ops.pdf_identity_text(lexical)),)),
        If(
            kind == "number",
            (Return(func.ops.pdf_identity_scalar("i", _utf8(cast(value, Text())))),),
        ),
        If(
            kind == "object",
            (
                If(
                    or_(
                        select(func.count()).select_from(keys).scalar_subquery() != 1,
                        ~value.has_key("native_float64"),
                        hexadecimal.op("!~")("^[0-9a-f]{16}$"),
                    ),
                    (Raise("invalid native binary64 inline representation", "23514"),),
                ),
                Return(func.ops.pdf_identity_scalar("f", _bytes(hexadecimal))),
            ),
        ),
        Raise(literal("unsupported inline scalar kind ").op("||")(kind), "23514"),
    )
    return _private_program(
        "pdf_identity_inline",
        (("p_value", pg_type("jsonb")),),
        "bytea",
        body,
        (Local("kind_", pg_type("text"), func.jsonb_typeof(value)),),
        immutable=True,
        strict=True,
    )


def _ascii_key_identity():
    value = core_variable("p_text", Text())
    indices = (
        func.generate_series(1, func.char_length(value))
        .table_valued(column("i", Integer()))
        .render_derived()
    )
    codes = select(
        indices.c.i, func.ascii(func.substr(value, indices.c.i, 1)).label("code")
    ).subquery()
    code = codes.c.code
    escape = func.chr(92, type_=Text())
    supplementary = code - 65536
    escaped = case(
        (code.in_((34, 92)), escape.op("||")(func.chr(code))),
        *(
            (code == number, escape.op("||")(letter))
            for number, letter in (
                (8, "b"),
                (9, "t"),
                (10, "n"),
                (12, "f"),
                (13, "r"),
            )
        ),
        (and_(code.between(32, 126), code.not_in((34, 92))), func.chr(code)),
        (code <= 65535, escape.op("||")("u").op("||")(func.lpad(func.to_hex(code), 4, "0"))),
        else_=escape.op("||")("u")
        .op("||")(func.to_hex(55296 + cast(supplementary, Integer()).op("/")(1024)))
        .op("||")(escape)
        .op("||")("u")
        .op("||")(func.to_hex(56320 + supplementary % 1024)),
    )
    interior = select(
        func.string_agg(escaped, aggregate_order_by(literal(""), codes.c.i))
    ).select_from(codes)
    return _private_program(
        "pdf_identity_ascii_string",
        (("p_text", pg_type("text")),),
        "text",
        (
            If(
                value.collate("C").op("!~")("[^ -~]"), (Return(cast(func.to_jsonb(value), Text())),)
            ),
            Return(literal('"').op("||")(interior.scalar_subquery()).op("||")('"')),
        ),
        immutable=True,
        strict=True,
    )


def _stream_identity(model, product, revision, placement_params):
    streams = model.tables["ops.pdf_artifact_stream"]
    stream_id, profile, length, root = (
        core_variable("p_stream", streams.c.stream_id.type),
        *(
            _row_value("stream_", streams, field)
            for field in ("encoding_profile", "byte_length", "byte_root")
        ),
    )
    return _private_program(
        "pdf_identity_stream_scalar",
        (*placement_params, ("p_stream", column_type(streams.c.stream_id))),
        "bytea",
        (
            SelectInto(
                select(core_relation_row(streams))
                .select_from(streams)
                .where(
                    *_placed(streams, product, revision),
                    streams.c.stream_id == stream_id,
                ),
                ("stream_",),
                strict=True,
            ),
            If(
                profile.in_(("pdf-record-native-json-v1", "pdf-companion-json-field-v1")),
                (Return(_frame("y", length, _bytes(root))),),
            ),
            If(
                profile.op("~")("^pdf-record-scalar-v1:[anbifsyd]$"),
                (Return(_frame(func.right(profile, 1), length, _bytes(root))),),
            ),
            Raise("stream is not a native scalar profile", "23514"),
        ),
        (Local("stream_", streams),),
        strict=True,
    )


def _companion_identity(model, product, revision, placement_params):
    fields = model.tables["kb.pdf_record_companion_field"]
    streams = model.tables["ops.pdf_artifact_stream"]
    family, local, field, body = (
        core_variable("p_family", fields.c.family.type),
        core_variable("p_local", fields.c.local_id.type),
        core_variable("p_field", fields.c.field_name.type),
        core_variable("p_body", JSONB()),
    )
    stream_id = _row_value("field_", fields, "stream_id")
    scalar_kind = _row_value("field_", fields, "scalar_kind")
    encoding = _row_value("stream_", streams, "encoding_profile")
    select_field = SelectInto(
        select(core_relation_row(fields))
        .select_from(fields)
        .where(
            *_placed(fields, product, revision),
            fields.c.family == family,
            fields.c.local_id == local,
            fields.c.field_name == field,
        ),
        ("field_",),
    )
    select_stream = SelectInto(
        select(core_relation_row(streams))
        .select_from(streams)
        .where(
            *_placed(streams, product, revision),
            streams.c.stream_id == stream_id,
        ),
        ("stream_",),
        strict=True,
    )
    metadata = family == "native_metadata"
    logical = body["payload_logical_digest"].astext
    return _private_program(
        "pdf_identity_companion_scalar",
        (
            *placement_params,
            ("p_family", column_type(fields.c.family)),
            ("p_local", column_type(fields.c.local_id)),
            ("p_field", column_type(fields.c.field_name)),
            ("p_body", pg_type("jsonb")),
        ),
        "bytea",
        (
            select_field,
            If(
                core_variable("found", Boolean()),
                (
                    If(
                        body.has_key(field),
                        (
                            Raise(
                                "companion field has competing inline and external values", "23514"
                            ),
                        ),
                    ),
                    select_stream,
                    If(
                        and_(field == "value", metadata, body["kind"].astext == FAMILY),
                        (
                            If(
                                or_(
                                    scalar_kind != "y",
                                    encoding != PROFILE,
                                    body["payload_codec"].astext.is_distinct_from(encoding),
                                    func.coalesce(logical, "").op("!~")("^[0-9a-f]{64}$"),
                                    func.coalesce(body["payload_schema_digest"].astext, "").op(
                                        "!~"
                                    )("^[0-9a-f]{64}$"),
                                ),
                                (Raise("structured companion identity profile differs", "23514"),),
                            ),
                            Return(
                                _frame(
                                    "y",
                                    32,
                                    func.sha256(
                                        _utf8("pdf-ocr-candidate-logical-v1").op("||")(
                                            _bytes(logical)
                                        )
                                    ),
                                )
                            ),
                        ),
                    ),
                    If(
                        or_(
                            and_(
                                field == "value",
                                or_(
                                    ~metadata,
                                    scalar_kind != "y",
                                    encoding != "pdf-companion-json-field-v1",
                                ),
                            ),
                            and_(
                                field == "text",
                                or_(
                                    family != "occurrence",
                                    scalar_kind != "s",
                                    encoding != "pdf-record-scalar-v1:s",
                                ),
                            ),
                        ),
                        (Raise("companion field profile differs", "23514"),),
                    ),
                    Return(func.ops.pdf_identity_stream_scalar(product, revision, stream_id)),
                ),
            ),
            If(
                metadata, (Raise("metadata value requires its declared JSON byte stream", "23514"),)
            ),
            If(~body.has_key(field), (Return(func.ops.pdf_identity_scalar("a", _bytes(""))),)),
            If(
                func.jsonb_typeof(body[field]).not_in(("null", "string")),
                (Raise("occurrence text must be string or null", "23514"),),
            ),
            Return(func.ops.pdf_identity_inline(body[field])),
        ),
        (Local("field_", fields), Local("stream_", streams)),
        strict=True,
    )


def _fold_digest(model, product, revision, placement_params):
    streams = model.tables["ops.pdf_artifact_stream"]
    stream = core_variable("stream_", streams.c.stream_id.type)
    digest = core_variable("digest_", BYTEA())
    frames = (
        func.ops.pdf_record_identity_frames(product, revision, True)
        .table_valued(column("frame", BYTEA()))
        .render_derived()
    )
    return _private_program(
        "pdf_record_logical_identity",
        placement_params,
        "text",
        (
            ForQuery(
                ("stream_",),
                select(streams.c.stream_id).where(*_placed(streams, product, revision)),
                (Perform(func.ops.pdf_identity_verify_artifact(product, revision, stream)),),
            ),
            SelectInto(select(frames.c.frame), ("digest_",), strict=True),
            Return(func.encode(digest, "hex")),
        ),
        (Local("stream_", column_type(streams.c.stream_id)), Local("digest_", pg_type("bytea"))),
    )


def pdf_record_logical_identity_programs(
    *, target_metadata: MetaData | None = None
) -> tuple[ProgramDeclaration, ...]:
    """Own scalar/fold routines; frame and target providers keep their own declarations."""
    from .metadata import get_metadata

    model = get_metadata() if target_metadata is None else target_metadata
    header = model.tables["ops.pdf_record_document"]
    params = (
        ("p_product", column_type(header.c.product_id)),
        ("p_revision", column_type(header.c.revision_id)),
    )
    product = core_variable("p_product", header.c.product_id.type)
    revision = core_variable("p_revision", header.c.revision_id.type)
    return (
        _text_identity(),
        _inline_identity(),
        _ascii_key_identity(),
        _stream_identity(model, product, revision, params),
        _companion_identity(model, product, revision, params),
        _fold_digest(model, product, revision, params),
    )


def pdf_record_logical_identity_sql(*, target_metadata: MetaData | None = None) -> str:
    """Keep the exact interleaved capture order of the three producing owners."""
    from .metadata import get_metadata
    from .pdf_identity_frames_native import pdf_identity_frame_declarations
    from .pdf_target_identity_native import logical_target_identity

    model = get_metadata() if target_metadata is None else target_metadata
    programs = pdf_record_logical_identity_programs(target_metadata=model)

    def rendered(program):
        return program.routine.render(), native_privilege_sql(
            program.identity, "PUBLIC", grant=False
        )

    return native_sql_script(
        (
            *(statement for program in programs[:-1] for statement in rendered(program)),
            *logical_target_identity(model),
            *pdf_identity_frame_declarations(model),
            *rendered(programs[-1]),
        )
    )
