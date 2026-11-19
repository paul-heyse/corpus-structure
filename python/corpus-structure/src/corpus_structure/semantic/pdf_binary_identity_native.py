"""Lower the portable PDF binary identity protocol to typed PostgreSQL programs."""

from pglast import ast
from sqlalchemy import (
    BigInteger,
    Boolean,
    Integer,
    MetaData,
    Text,
    and_,
    any_,
    case,
    cast,
    func,
    literal,
    or_,
    select,
)
from sqlalchemy.dialects.postgresql import ARRAY, BYTEA, array

from corpus_structure.schema.integrity import role_name

from .native_objects import INTERNAL_PROGRAM, native_privilege_sql, native_sql_script
from .native_program import (
    Assign,
    Block,
    Continue,
    If,
    Local,
    NativeRoutine,
    Parameter,
    Raise,
    Return,
    ReturnQuery,
    SelectInto,
    While,
    column_type,
    core_relation_row,
    core_variable,
    pg_type,
)
from .native_program_registry import ProgramDeclaration
from .pdf_record_digest_native import _bytes, _frame, _placed, _row_value, _utf8
from .pdf_record_identity import _END, _START, _STEP, BLOCK_BYTES, MAX_FRAME_BYTES


def _concat(first, *remaining):
    result = first
    for value in remaining:
        result = result.op("||")(value)
    return result


def _length(value):
    return func.int8send(cast(value, BigInteger()), type_=BYTEA())


def _size(value):
    return func.octet_length(value, type_=Integer())


def _array_type(datatype):
    result = pg_type(datatype)
    result.arrayBounds = (ast.Integer(ival=-1),)
    return result


def _private_routine(name, params, kind, steps, locals_=(), *, immutable=False, strict=False):
    return NativeRoutine(
        "ops",
        name,
        parameters=tuple(Parameter(label, type_) for label, type_ in params),
        returns=pg_type(kind),
        body=Block(tuple(steps), tuple(locals_)),
        search_path=("pg_catalog", "pg_temp"),
        volatility="immutable" if immutable else "stable",
        strict=strict,
    )


def _declaration(routine: NativeRoutine) -> ProgramDeclaration:
    return ProgramDeclaration(
        routine,
        source="target-current:PDF publication",
        owner=role_name("publisher"),
        access=INTERNAL_PROGRAM,
    )


def _render_capture(declarations: tuple[ProgramDeclaration, ...]) -> str:
    return native_sql_script(
        statement
        for declaration in declarations
        for statement in (
            declaration.routine.render(),
            native_privilege_sql(declaration.identity, "PUBLIC", grant=False),
        )
    )


def pdf_binary_identity_programs() -> tuple[ProgramDeclaration, ...]:
    """Keep byte framing, folds, UTF-8 admissibility and canonical scalar tags together."""
    payload = core_variable("p_payload", BYTEA())
    tag = core_variable("p_tag", BYTEA())
    domain = core_variable("p_domain", Text())
    state = core_variable("p_state", BYTEA())
    ordinal = core_variable("p_ordinal", BigInteger())
    count = core_variable("p_count", BigInteger())
    length = core_variable("p_length", BigInteger())
    payload_parameter = ("p_payload", pg_type("bytea"))
    state_parameter = ("p_state", pg_type("bytea"))

    def frame(tag, payload):
        return func.ops.pdf_identity_frame(_utf8(tag), payload, type_=BYTEA())

    def declare(name, params, returns, body, locals_=()):
        return _private_routine(
            "pdf_identity_" + name,
            params,
            returns,
            body,
            locals_,
            immutable=True,
            strict=True,
        )

    start = "pdf_identity_fold_start"
    start_declaration = NativeRoutine(
        "ops",
        start,
        parameters=(Parameter("p_domain", pg_type("text")),),
        returns=pg_type("bytea"),
        search_path=("pg_catalog", "pg_temp"),
        volatility="immutable",
        strict=True,
        body=select(func.sha256(_concat(_bytes(_START.hex()), frame("D", _utf8(domain))))),
    )
    fold_state = core_variable("state", BYTEA())
    block = core_variable("block_", BYTEA())
    block_index = core_variable("ordinal", BigInteger())
    offset = core_variable("offset_", Integer())
    names = core_variable("p_names", ARRAY(Text()))
    scalars = core_variable("p_scalars", ARRAY(BYTEA()))
    schema, family, key = (
        core_variable(name, Text()) for name in ("p_schema", "p_family", "p_key")
    )
    seen = core_variable("names_", ARRAY(Text()))
    index = core_variable("i", Integer())
    cardinality = core_variable("n", Integer())
    body = core_variable("body_", BYTEA())
    name = names[index]
    scalar = scalars[index]
    scalar_tag = func.get_byte(scalar, 0)
    field_length = func.substr(scalar, 2, 8)
    zero, one, eight = (_length(literal(value)) for value in (0, 1, 8))
    frame_program = (
        If(
            or_(
                schema == "",
                family == "",
                key == "",
                cardinality != func.cardinality(scalars),
                func.coalesce(func.array_lower(names, 1), 1) != 1,
                func.coalesce(func.array_lower(scalars, 1), 1) != 1,
            ),
            (Raise("record schema/family/key/fields invalid", "23514"),),
        ),
        Assign(
            "body_",
            _concat(frame("s", _utf8(schema)), frame("f", _utf8(family)), frame("k", _utf8(key))),
        ),
        While(
            index <= cardinality,
            (
                If(
                    or_(
                        name.is_(None),
                        name == "",
                        name == any_(seen),
                        scalar.is_(None),
                        _size(scalar) != 41,
                        scalar_tag.not_in(tuple(map(ord, "anbifsyd"))),
                        func.get_byte(scalar, 1) > 127,
                    ),
                    (Raise("record field name/scalar invalid", "23514"),),
                ),
                If(
                    or_(
                        and_(scalar_tag.in_((ord("a"), ord("n"))), field_length != zero),
                        and_(scalar_tag == ord("b"), field_length != one),
                        and_(scalar_tag == ord("f"), field_length != eight),
                    ),
                    (Raise("scalar kind has an invalid payload length", "23514"),),
                ),
                Assign("body_", _concat(body, frame("n", _utf8(name)), scalar)),
                If(
                    _size(body) + 8 > MAX_FRAME_BYTES - 9,
                    (Raise("record frame exceeds 64 KiB; lower collections into rows", "23514"),),
                ),
                Assign("names_", func.array_append(seen, name)),
                Assign("i", index + 1),
            ),
        ),
        If(_size(body) + 17 > MAX_FRAME_BYTES, (Raise("record frame exceeds 64 KiB", "23514"),)),
        Return(frame("R", _concat(_length(cardinality), body))),
    )
    routines = (
        declare(
            "frame",
            (("p_tag", pg_type("bytea")), payload_parameter),
            "bytea",
            (
                If(
                    or_(_size(tag) != 1, _size(payload) > MAX_FRAME_BYTES),
                    (Raise("identity frame requires one-byte tag and bounded payload", "23514"),),
                ),
                Return(_concat(tag, _length(_size(payload)), payload)),
            ),
        ),
        start_declaration,
        declare(
            "fold_step",
            (state_parameter, ("p_ordinal", pg_type("int8")), payload_parameter),
            "bytea",
            (
                If(
                    or_(_size(state) != 32, ordinal < 0),
                    (Raise("identity fold state/ordinal invalid", "23514"),),
                ),
                Return(
                    func.sha256(
                        _concat(_bytes(_STEP.hex()), state, _length(ordinal), frame("F", payload))
                    )
                ),
            ),
        ),
        declare(
            "fold_finish",
            (state_parameter, ("p_count", pg_type("int8")), ("p_length", pg_type("int8"))),
            "bytea",
            (
                If(
                    or_(_size(state) != 32, count < 0, length < 0),
                    (Raise("identity fold final inventory invalid", "23514"),),
                ),
                Return(
                    func.sha256(_concat(_bytes(_END.hex()), state, _length(count), _length(length)))
                ),
            ),
        ),
        declare(
            "byte_root",
            (payload_parameter,),
            "bytea",
            (
                While(
                    offset <= _size(payload),
                    (
                        Assign("block_", func.substr(payload, offset, BLOCK_BYTES)),
                        Assign(
                            "state",
                            func.ops.pdf_identity_fold_step(fold_state, block_index, block),
                        ),
                        Assign("offset_", offset + _size(block)),
                        Assign("ordinal", block_index + 1),
                    ),
                ),
                Return(
                    func.ops.pdf_identity_fold_finish(
                        fold_state, block_index, cast(_size(payload), BigInteger())
                    )
                ),
            ),
            (
                Local("state", pg_type("bytea"), func.ops.pdf_identity_fold_start("bytes")),
                Local("ordinal", pg_type("int8"), literal(0)),
                Local("offset_", pg_type("int4"), literal(1)),
                Local("block_", pg_type("bytea")),
            ),
        ),
        _utf8_validation(payload, payload_parameter),
        _canonical_scalar(payload, payload_parameter),
        declare(
            "record_frame",
            (
                ("p_schema", pg_type("text")),
                ("p_family", pg_type("text")),
                ("p_key", pg_type("text")),
                ("p_names", _array_type("text")),
                ("p_scalars", _array_type("bytea")),
            ),
            "bytea",
            frame_program,
            (
                Local("body_", pg_type("bytea")),
                Local("i", pg_type("int4"), literal(1)),
                Local("n", pg_type("int4"), func.cardinality(names)),
                Local("names_", _array_type("text"), array((), type_=Text())),
            ),
        ),
    )
    return tuple(_declaration(routine) for routine in routines)


def pdf_binary_identity_sql() -> str:
    """Render the captured binary identity statements and existing ACL projection."""
    return _render_capture(pdf_binary_identity_programs())


def _utf8_validation(payload, payload_parameter):
    # PostgreSQL text conversion rejects NUL even when the byte stream is valid UTF-8.
    index, first, second, width, continuation = (
        core_variable(name, Integer()) for name in ("i", "c", "c2", "width_", "j")
    )

    def byte(position):
        return func.get_byte(payload, position)

    return _private_routine(
        "pdf_identity_utf8",
        (payload_parameter,),
        "bool",
        (
            While(
                index < _size(payload),
                (
                    Assign("c", byte(index)),
                    If(first < 128, (Assign("i", index + 1), Continue())),
                    Assign(
                        "width_",
                        case(
                            (first.between(194, 223), 2),
                            (first.between(224, 239), 3),
                            (first.between(240, 244), 4),
                        ),
                    ),
                    If(
                        or_(width.is_(None), index + width > _size(payload)),
                        (Return(literal(False)),),
                    ),
                    Assign("c2", byte(index + 1)),
                    If(
                        or_(
                            and_(first == 224, second < 160),
                            and_(first == 237, second >= 160),
                            and_(first == 240, second < 144),
                            and_(first == 244, second >= 144),
                        ),
                        (Return(literal(False)),),
                    ),
                    Assign("j", literal(1)),
                    While(
                        continuation < width,
                        (
                            If(
                                ~byte(index + continuation).between(128, 191),
                                (Return(literal(False)),),
                            ),
                            Assign("j", continuation + 1),
                        ),
                    ),
                    Assign("i", index + width),
                ),
            ),
            Return(literal(True)),
        ),
        (
            Local("i", pg_type("int4"), literal(0)),
            Local("c", pg_type("int4")),
            Local("c2", pg_type("int4")),
            Local("width_", pg_type("int4")),
            Local("j", pg_type("int4")),
        ),
        immutable=True,
        strict=True,
    )


def _canonical_scalar(payload, payload_parameter):
    tag = core_variable("p_kind", Text())
    valid = core_variable("valid_", Boolean())
    text = func.convert_from(payload, "UTF8", type_=Text())
    float_tag = func.get_byte(payload, 0, type_=Integer()).bitwise_and(127)
    float_exponent = func.get_byte(payload, 1, type_=Integer()).bitwise_and(240)
    return _private_routine(
        "pdf_identity_scalar",
        (("p_kind", pg_type("text")), payload_parameter),
        "bytea",
        (
            Assign(
                "valid_",
                case(
                    (tag.in_(("a", "n")), _size(payload) == 0),
                    (
                        tag == "b",
                        case(
                            (_size(payload) == 1, func.get_byte(payload, 0).in_((0, 1))),
                            else_=False,
                        ),
                    ),
                    (tag == "i", text.op("~")("^(0|-?[1-9][0-9]*)$")),
                    (
                        tag == "f",
                        case(
                            (_size(payload) == 8, ~and_(float_tag == 127, float_exponent == 240)),
                            else_=False,
                        ),
                    ),
                    (tag == "s", func.ops.pdf_identity_utf8(payload)),
                    (tag == "y", literal(True)),
                    (tag == "d", text.op("~")("^[01]:(0|[1-9][0-9]*):(0|-?[1-9][0-9]*)$")),
                    else_=False,
                ),
            ),
            If(
                ~valid,
                (Raise(literal("noncanonical PDF record scalar kind ").op("||")(tag), "23514"),),
            ),
            Return(_frame(tag, _size(payload), func.ops.pdf_identity_byte_root(payload))),
        ),
        (Local("valid_", pg_type("bool")),),
        immutable=True,
        strict=True,
    )


def pdf_artifact_identity_programs(model: MetaData) -> tuple[ProgramDeclaration, ...]:
    """Verify a shared artifact before its descriptor contributes to a record digest."""
    streams = model.tables["ops.pdf_artifact_stream"]
    inputs = (
        ("p_product", streams.c.product_id),
        ("p_revision", streams.c.revision_id),
        ("p_stream", streams.c.stream_id),
    )
    product, revision, stream = (core_variable(name, field.type) for name, field in inputs)
    parameters = tuple(Parameter(name, column_type(field)) for name, field in inputs)
    profile, length, root = (
        _row_value("stream_", streams, name)
        for name in ("encoding_profile", "byte_length", "byte_root")
    )
    returns = pg_type("record")
    returns.setof = True
    name = "pdf_identity_verify_artifact"
    routine = NativeRoutine(
        "ops",
        name,
        parameters=parameters,
        returns=returns,
        table_columns=(("actual_length", pg_type("int8")), ("actual_byte_root", pg_type("bytea"))),
        search_path=("pg_catalog", "pg_temp"),
        volatility="stable",
        body=Block(
            (
                SelectInto(
                    select(core_relation_row(streams))
                    .select_from(streams)
                    .where(*_placed(streams, product, revision), streams.c.stream_id == stream),
                    ("stream_",),
                    strict=True,
                ),
                If(
                    ~func.ops.pdf_shared_stream_ready(product, profile, length, root),
                    (Raise("artifact lacks its project-scoped actual fold receipt", "23514"),),
                ),
                ReturnQuery(select(length, _bytes(root))),
            ),
            (Local("stream_", streams),),
        ),
    )
    return (_declaration(routine),)


def pdf_artifact_identity_sql(model: MetaData) -> str:
    """Render the captured artifact verifier and its existing ACL projection."""
    return _render_capture(pdf_artifact_identity_programs(model))
