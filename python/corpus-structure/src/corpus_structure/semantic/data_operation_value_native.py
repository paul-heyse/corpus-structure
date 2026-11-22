"""Compile the declared value codec and fixed JSON wire shape for PostgreSQL."""

from typing import get_args, get_type_hints

from pglast import ast
from sqlalchemy import (
    BigInteger,
    Boolean,
    Date,
    DateTime,
    Integer,
    Numeric,
    Text,
    and_,
    any_,
    case,
    cast,
    column,
    extract,
    func,
    literal,
    or_,
    select,
)
from sqlalchemy.dialects.postgresql import (
    ARRAY,
    DOUBLE_PRECISION,
    JSONB,
    JSONPATH,
    aggregate_order_by,
)

from .data_operation_identity import ENCODING_VERSION
from .data_operation_values import CollectionValue, OptionalValue
from .native_objects import native_sql_script
from .native_program import (
    Assign,
    Block,
    If,
    Local,
    NativeRoutine,
    Parameter,
    Raise,
    Return,
    SelectInto,
    core_variable,
    pg_type,
)
from .value_codec_core import DECIMAL_LIMIT_MESSAGE

_NON_VALUES = (
    "null",
    *(tag for tag in get_args(get_type_hints(OptionalValue)["state"]) if tag != "present"),
)
_COLLECTIONS = ("sequence", *get_args(get_type_hints(CollectionValue)["kind"]))
_TEXT = ("string", "date", "datetime", "float", "integer", "decimal")


def _json(value):
    return cast(literal(value), JSONB())


def canonical_text_digest(value):
    """Hash text already encoded by the native canonical JSON owner."""
    return func.encode(func.sha256(func.convert_to(value, "UTF8")), "hex")


def _meaning_digest(meaning):
    return canonical_text_digest(func.data.canonical_json(meaning))


def _identity_expression(domain, meaning):
    return domain.op("||")(":").op("||")(
        _meaning_digest(func.jsonb_build_array("ddo", domain, ENCODING_VERSION, meaning))
    )


def json_observation_identity(domain: str, datum):
    """Hash native-assembled nonnull JSON facts through their owned meaning codec.

    The codec emits canonical meanings itself, so no caller-supplied preencoded
    meaning enters this composition and no second normalization is needed.
    """
    return _identity_expression(literal(domain), func.data.ddo_json_meaning(datum))


def _members(value, *, ordinality=False):
    fn = func.jsonb_array_elements(value)
    field = column("value", JSONB())
    if ordinality:
        return fn.table_valued(field, with_ordinality="ordinal").render_derived()
    return fn.table_valued(field)


def canonical_identity_programs(*, decimal_digits: int):
    """Declare the canonical JSON traversal and finite decimal lexical projection."""
    value = core_variable("p", JSONB())
    elements = _members(value, ordinality=True)
    fields = func.jsonb_each(value).table_valued(column("key", Text()), column("value", JSONB()))

    def enclosed(start, entries, order, relation, end):
        joined = select(func.string_agg(entries, aggregate_order_by(literal(","), order)))
        body = func.coalesce(joined.select_from(relation).scalar_subquery(), "")
        return literal(start).concat(body).concat(end)

    array_json = enclosed(
        "[", func.data.canonical_json(elements.c.value), elements.c.ordinal, elements, "]"
    )
    # Tagged values are arrays with scalar leaves. JSONB already emits their
    # scalar text and array order, so only separators outside strings differ.
    # Arrays containing objects retain the ordered traversal for their keys.
    nested_objects = cast(literal('strict $.** ? (@.type() == "object")'), JSONPATH())
    compact_array = func.regexp_replace(
        cast(value, Text()).collate("C"), r'("(?:[^"\\]|\\.)*")|[[:space:]]+', r"\1", "g"
    )
    array_json = case(
        (func.jsonb_path_exists(value, nested_objects), array_json), else_=compact_array
    )
    object_json = enclosed(
        "{",
        cast(func.to_json(fields.c.key), Text())
        .concat(":")
        .concat(func.data.canonical_json(fields.c.value)),
        fields.c.key.collate("C"),
        fields,
        "}",
    )
    canonical_json = NativeRoutine(
        "data",
        "canonical_json",
        parameters=(Parameter("p", pg_type("jsonb")),),
        returns=pg_type("text"),
        body=select(
            case(
                (func.jsonb_typeof(value) == "array", array_json),
                (func.jsonb_typeof(value) == "object", object_json),
                else_=cast(value, Text()),
            )
        ),
        search_path=("pg_catalog", "pg_temp"),
        volatility="immutable",
        strict=True,
    )
    raw, whole, fraction, digits, fixed, exponent_digits = (
        core_variable(name, Text())
        for name in ("raw", "whole", "fraction", "digits", "fixed", "exponent_digits")
    )
    parts = core_variable("parts", ARRAY(Text()))
    point, exponent = (core_variable(name, BigInteger()) for name in ("point", "exponent"))
    negative = core_variable("negative", Boolean())
    text_type = pg_type("text")
    parts_type = pg_type("text")
    parts_type.arrayBounds = (ast.Integer(ival=-1),)
    leading_zeroes = literal("0.").concat(func.repeat("0", cast(-point, Integer()))).concat(digits)
    trailing_zeroes = digits.concat(func.repeat("0", cast(point - func.length(digits), Integer())))
    split_digits = (
        cast(func.left(digits, cast(point, Integer())), Text())
        .concat(".")
        .concat(func.substr(digits, cast(point + 1, Integer())))
    )
    decimal = _value(
        "decimal_canonical",
        (Parameter("raw", text_type),),
        "text",
        (
            If(
                raw.op("!~")("^[+-]?([0-9]+([.][0-9]*)?|[.][0-9]+)([eE][+-]?[0-9]+)?$"),
                (Raise("invalid finite decimal lexical", "23514"),),
            ),
            Assign("negative", func.left(raw, 1) == "-"),
            Assign("parts", func.regexp_split_to_array(func.ltrim(raw, "+-"), "[eE]")),
            Assign("whole", func.split_part(parts[1], ".", 1)),
            Assign("fraction", func.split_part(parts[1], ".", 2)),
            Assign("digits", func.ltrim(whole.concat(fraction), "0")),
            If(digits == "", (Return(literal("0")),)),
            Assign(
                "exponent_digits", func.ltrim(func.ltrim(func.coalesce(parts[2], "0"), "+-"), "0")
            ),
            # Eleven significant exponent digits cannot be offset by a PostgreSQL text operand.
            If(func.length(exponent_digits) > 10, (Raise(DECIMAL_LIMIT_MESSAGE, "23514"),)),
            Assign(
                "exponent",
                case((func.left(parts[2], 1) == "-", -1), else_=1)
                * cast(func.coalesce(func.nullif(exponent_digits, ""), "0"), BigInteger()),
            ),
            Assign("point", exponent + func.length(digits) - func.length(fraction)),
            Assign("digits", func.rtrim(digits, "0")),
            If(
                func.greatest(point, 1) + func.greatest(func.length(digits) - point, 0)
                > decimal_digits,
                (Raise(DECIMAL_LIMIT_MESSAGE, "23514"),),
            ),
            If(
                point <= 0,
                (Assign("fixed", leading_zeroes),),
                (
                    If(
                        point >= func.length(digits),
                        (Assign("fixed", trailing_zeroes),),
                        (Assign("fixed", split_digits),),
                    ),
                ),
            ),
            Return(case((negative, "-"), else_="").concat(fixed)),
        ),
        (
            Local("parts", parts_type),
            *(
                Local(name, text_type)
                for name in ("whole", "fraction", "digits", "fixed", "exponent_digits")
            ),
            Local("point", pg_type("int8")),
            Local("exponent", pg_type("int8")),
            Local("negative", pg_type("bool")),
        ),
    )
    from corpus_structure.schema.integrity import role_name

    from .native_objects import INTERNAL_PROGRAM
    from .native_program_registry import ProgramDeclaration

    return tuple(
        ProgramDeclaration(
            routine,
            source="target-current:identity.sql",
            owner=role_name("publisher"),
            access=INTERNAL_PROGRAM,
        )
        for routine in (canonical_json, decimal)
    )


def _lexical_timestamp(lexical):
    instant = cast(lexical, DateTime(timezone=True))
    utc = func.timezone("UTC", instant)
    suffix = case(
        (
            cast(extract("microseconds", instant), BigInteger()) % 1_000_000 != 0,
            literal(".").op("||")(func.to_char(utc, "US")),
        ),
        else_="",
    )
    return func.to_char(utc, 'YYYY-MM-DD"T"HH24:MI:SS').op("||")(suffix).op("||")("+00:00")


def _field_guard():
    body = core_variable("p", JSONB())
    required = core_variable("required", ARRAY(Text()))
    optional = core_variable("optional", ARRAY(Text()))
    keys = func.jsonb_object_keys(body).table_valued(column("key", Text())).render_derived()
    required_keys = func.unnest(required).table_valued(column("key", Text())).render_derived()
    text_array = pg_type("text")
    text_array.arrayBounds = (ast.Integer(ival=-1),)
    return NativeRoutine(
        "ops",
        "ddo_fields",
        parameters=(
            Parameter("p", pg_type("jsonb")),
            Parameter("required", text_array),
            Parameter(
                "optional", text_array, ast.TypeCast(arg=ast.A_ArrayExpr(), typeName=text_array)
            ),
        ),
        returns=pg_type("void"),
        volatility="immutable",
        search_path=("pg_catalog", "pg_temp"),
        body=Block(
            (
                If(
                    or_(
                        func.jsonb_typeof(body).is_distinct_from("object"),
                        select(1)
                        .select_from(required_keys)
                        .where(~body.has_key(required_keys.c.key))
                        .exists(),
                        select(1)
                        .select_from(keys)
                        .where(~(keys.c.key == any_(required.op("||")(optional))))
                        .exists(),
                    ),
                    (Raise("DDO wire fields differ from the fixed operation contract", "23514"),),
                ),
            )
        ),
    )


def _value(name, parameters, result, steps, locals_=()):
    return NativeRoutine(
        "data",
        name,
        parameters=parameters,
        returns=pg_type(result),
        body=Block(tuple(steps), tuple(locals_)),
        search_path=("pg_catalog", "pg_temp"),
        volatility="immutable",
        strict=True,
    )


def _normalize():
    body = core_variable("v", JSONB())
    tag = core_variable("tag", Text())
    value = body[1]
    lexical = core_variable("lexical", Text())
    result = core_variable("result", JSONB())
    size = core_variable("n", Integer())
    items = _members(value, ordinality=True)
    ordered = select(
        func.coalesce(
            func.jsonb_agg(
                aggregate_order_by(func.data.ddo_normalize(items.c.value), items.c.ordinal)
            ),
            _json("[]"),
        )
    ).select_from(items)
    members = _members(result)
    distinct = select(members.c.value).distinct().subquery("distinct_members")
    pairs = _members(value)
    pair = pairs.c.value
    mapping = select(
        func.coalesce(
            func.jsonb_agg(
                aggregate_order_by(
                    func.jsonb_build_array(pair[0], func.data.ddo_normalize(pair[1])),
                    pair[0].astext.collate("C"),
                )
            ),
            _json("[]"),
        )
    ).select_from(pairs)

    def sorted_collection(rows):
        value = rows.c.value
        canonical = func.convert_to(func.data.canonical_json(value), "UTF8")
        return select(
            func.coalesce(
                func.jsonb_agg(aggregate_order_by(value, canonical)),
                _json("[]"),
            )
        ).select_from(rows)

    def refuse(pattern, message, *conditions):
        return If(or_(lexical.op("!~")(pattern), *conditions), (Raise(message, "P0001"),))

    convert = Assign("lexical", func.data.decimal_canonical(lexical))
    return _value(
        "ddo_normalize",
        (Parameter("v", pg_type("jsonb")),),
        "jsonb",
        (
            If(
                or_(
                    func.jsonb_typeof(body) != "array",
                    func.jsonb_array_length(body) == 0,
                    func.jsonb_typeof(body[0]) != "string",
                ),
                (Raise("DDO semantic value must be tagged", "23514"),),
            ),
            Assign("tag", body[0].astext),
            Assign("n", func.jsonb_array_length(body)),
            If(
                or_(
                    and_(tag.in_(_NON_VALUES), size == 1),
                    and_(tag == "boolean", size == 2, func.jsonb_typeof(value) == "boolean"),
                ),
                (Return(body),),
            ),
            If(
                and_(tag.in_(_TEXT), size == 2, func.jsonb_typeof(value) == "string"),
                (
                    Assign("lexical", value.astext),
                    If(
                        tag == "integer",
                        (refuse("^[+-]?[0-9]+$", "invalid integer meaning"), convert),
                    ),
                    If(
                        tag == "decimal",
                        (
                            refuse(
                                "^[+-]?([0-9]+([.][0-9]*)?|[.][0-9]+)([eE][+-]?[0-9]+)?$",
                                "invalid decimal meaning",
                            ),
                            convert,
                        ),
                    ),
                    If(
                        tag == "float",
                        (Assign("lexical", func.data.require_float_lexical(lexical)),),
                    ),
                    If(
                        tag == "date",
                        (
                            refuse(
                                "^[0-9]{4}-[0-9]{2}-[0-9]{2}$",
                                "date meaning requires canonical ISO date",
                                lexical != cast(cast(lexical, Date()), Text()),
                            ),
                        ),
                    ),
                    If(
                        tag == "datetime",
                        (
                            refuse(
                                "^[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}([.][0-9]{6})?[+]00:00$",
                                "datetime meaning requires canonical Python UTC ISO instant",
                                lexical.is_distinct_from(_lexical_timestamp(lexical)),
                            ),
                        ),
                    ),
                    Return(func.jsonb_build_array(tag, lexical)),
                ),
            ),
            If(
                and_(tag == "present", size == 2),
                (Return(func.jsonb_build_array(tag, func.data.ddo_normalize(value))),),
            ),
            If(
                and_(tag.in_(_COLLECTIONS), size == 2, func.jsonb_typeof(value) == "array"),
                (
                    SelectInto(ordered, ("result",)),
                    If(tag == "set", (SelectInto(sorted_collection(distinct), ("result",)),)),
                    If(tag == "bag", (SelectInto(sorted_collection(members), ("result",)),)),
                    Return(func.jsonb_build_array(tag, result)),
                ),
            ),
            If(
                and_(tag == "mapping", size == 2, func.jsonb_typeof(value) == "array"),
                (
                    If(
                        or_(
                            select(1)
                            .select_from(pairs)
                            .where(
                                or_(
                                    func.jsonb_typeof(pair) != "array",
                                    func.jsonb_array_length(pair) != 2,
                                    func.jsonb_typeof(pair[0]) != "string",
                                )
                            )
                            .exists(),
                            select(1)
                            .select_from(pairs)
                            .group_by(pair[0].astext)
                            .having(func.count() != 1)
                            .exists(),
                        ),
                        (Raise("invalid mapping members", "P0001"),),
                    ),
                    SelectInto(mapping, ("result",)),
                    Return(func.jsonb_build_array(tag, result)),
                ),
            ),
            Raise(
                literal("invalid or unsupported DDO semantic tag ").op("||")(
                    func.coalesce(tag, "<NULL>")
                ),
                "23514",
            ),
        ),
        (
            Local("tag", pg_type("text")),
            Local("n", pg_type("int4")),
            Local("lexical", pg_type("text")),
            Local("result", pg_type("jsonb")),
        ),
    )


def _json_meaning():
    value = core_variable("value", JSONB())
    kind = func.jsonb_typeof(value)
    members = _members(value, ordinality=True)
    mapping = func.jsonb_each(value).table_valued(column("key", Text()), column("value", JSONB()))
    normalized = func.data.ddo_json_meaning
    # Admitted typed payloads are nested arrays with scalar leaves. Emit their
    # existing JSON meaning in one ordered pass instead of invoking PL/pgSQL
    # recursively for every node and rebuilding each enclosing subtree.
    tokens = (
        func.regexp_matches(
            cast(value, Text()).collate("C"),
            r'"(?:[^"\\]|\\.)*"|\[|\]|,|null|true|false|-?[0-9]+(?:\.[0-9]+)?(?:[eE][+-]?[0-9]+)?',
            "g",
        )
        .table_valued(column("part", ARRAY(Text())), with_ordinality="ordinal")
        .render_derived(name="json_meaning_tokens")
    )
    token = tokens.c.part[1]
    fragment = case(
        (token == "[", '["sequence",['),
        (token == "]", "]]"),
        (token == ",", ","),
        (token == "null", '["null"]'),
        (token.in_(("true", "false")), literal('["boolean",').concat(token).concat("]")),
        (func.left(token, 1) == '"', literal('["string",').concat(token).concat("]")),
        else_=literal('["decimal",')
        .concat(cast(func.to_json(func.data.decimal_canonical(token)), Text()))
        .concat("]"),
    )
    scalar_array = cast(
        select(func.string_agg(fragment, aggregate_order_by(literal(""), tokens.c.ordinal)))
        .select_from(tokens)
        .scalar_subquery(),
        JSONB(),
    )
    nested_objects = cast(literal('strict $.** ? (@.type() == "object")'), JSONPATH())
    sequence = (
        select(
            func.coalesce(
                func.jsonb_agg(aggregate_order_by(normalized(members.c.value), members.c.ordinal)),
                _json("[]"),
            )
        )
        .select_from(members)
        .scalar_subquery()
    )
    ordered = (
        select(
            func.coalesce(
                func.jsonb_agg(
                    aggregate_order_by(
                        func.jsonb_build_array(mapping.c.key, normalized(mapping.c.value)),
                        mapping.c.key.collate("C"),
                    )
                ),
                _json("[]"),
            )
        )
        .select_from(mapping)
        .scalar_subquery()
    )
    return _value(
        "ddo_json_meaning",
        (Parameter("value", pg_type("jsonb")),),
        "jsonb",
        (
            If(kind == "null", (Return(func.jsonb_build_array("null")),)),
            If(kind.in_(("boolean", "string")), (Return(func.jsonb_build_array(kind, value)),)),
            If(
                kind == "number",
                (
                    Return(
                        func.jsonb_build_array(
                            "decimal", func.data.decimal_canonical(value[()].astext)
                        )
                    ),
                ),
            ),
            If(
                kind == "array",
                (
                    If(~func.jsonb_path_exists(value, nested_objects), (Return(scalar_array),)),
                    Return(func.jsonb_build_array("sequence", sequence)),
                ),
            ),
            If(kind == "object", (Return(func.jsonb_build_array("mapping", ordered)),)),
            Raise("unsupported JSON context value", "P0001"),
        ),
    )


def _decode():
    value = core_variable("v", JSONB())
    tag = value[0].astext
    payload = value[1]
    member = _members(payload, ordinality=True)
    pairs = _members(payload)
    sequence = (
        select(
            func.coalesce(
                func.jsonb_agg(
                    aggregate_order_by(func.data.ddo_json(member.c.value), member.c.ordinal)
                ),
                _json("[]"),
            )
        )
        .select_from(member)
        .scalar_subquery()
    )
    mapping = (
        select(
            func.coalesce(
                func.jsonb_object_agg(
                    pairs.c.value[0].astext, func.data.ddo_json(pairs.c.value[1])
                ),
                _json("{}"),
            )
        )
        .select_from(pairs)
        .scalar_subquery()
    )
    return _value(
        "ddo_json",
        (Parameter("v", pg_type("jsonb")),),
        "jsonb",
        (
            If(tag.in_(_NON_VALUES), (Return(_json("null")),)),
            If(tag.in_(("boolean", "string", "date", "datetime")), (Return(payload),)),
            If(
                tag == "float",
                (
                    Return(
                        func.to_jsonb(
                            cast(
                                func.data.require_float_lexical(payload.astext), DOUBLE_PRECISION()
                            )
                        )
                    ),
                ),
            ),
            If(
                tag.in_(("integer", "decimal")),
                (Return(func.to_jsonb(cast(payload.astext, Numeric()))),),
            ),
            If(tag == "present", (Return(func.data.ddo_json(payload)),)),
            If(tag.in_(_COLLECTIONS), (Return(sequence),)),
            If(tag == "mapping", (Return(mapping),)),
            Raise("unsupported semantic body", "P0001"),
        ),
    )


def data_operation_value_programs():
    from corpus_structure.schema.integrity import role_name

    from .native_objects import INTERNAL_PROGRAM, NativeProgramAccess
    from .native_program_registry import ProgramDeclaration

    value = core_variable("v", JSONB())
    domain = core_variable("domain", Text())
    key = core_variable("k", Text())
    body = Parameter("v", pg_type("jsonb"))
    members = _members(value[1])

    def native_sql_function(schema, name, params, kind, expression):
        return NativeRoutine(
            schema,
            name,
            parameters=params,
            returns=pg_type(kind),
            body=expression,
            volatility="immutable",
            strict=True,
            search_path=("pg_catalog", "pg_temp"),
        )

    routines = (
        _field_guard(),
        _normalize(),
        _json_meaning(),
        native_sql_function(
            "data",
            "ddo_identity",
            (Parameter("domain", pg_type("text")), body),
            "text",
            select(_identity_expression(domain, func.data.ddo_normalize(value))),
        ),
        native_sql_function("ops", "ddo_digest", (body,), "text", select(_meaning_digest(value))),
        native_sql_function(
            "data",
            "ddo_field",
            (body, Parameter("k", pg_type("text"))),
            "jsonb",
            select(
                members.c.value[1],
            ).where(members.c.value[0].astext == key),
        ),
        _decode(),
    )
    return tuple(
        ProgramDeclaration(
            routine,
            source="native/demand-values.sql",
            owner=role_name("publisher"),
            access=(
                NativeProgramAccess(purposes=("read", "write", "evaluate"))
                if routine.name == "ddo_field"
                else INTERNAL_PROGRAM
            ),
        )
        for routine in routines
    )


def data_operation_value_sql() -> str:
    return native_sql_script(item.render() for item in data_operation_value_programs())
