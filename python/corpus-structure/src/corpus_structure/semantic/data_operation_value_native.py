"""Compile the declared value codec and fixed JSON wire shape for PostgreSQL."""

from typing import get_args, get_type_hints

from pglast import ast
from sqlalchemy import (
    BigInteger,
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
from sqlalchemy.dialects.postgresql import ARRAY, DOUBLE_PRECISION, JSONB, aggregate_order_by

from .data_operation_identity import ENCODING_VERSION, CollectionValue, OptionalValue
from .native_objects import native_sql_script
from .native_program import (
    Assign,
    Block,
    If,
    Local,
    Parameter,
    Raise,
    Return,
    SelectInto,
    core_variable,
    function,
    pg_type,
    sql_function,
)

_NON_VALUES = (
    "null",
    *(tag for tag in get_args(get_type_hints(OptionalValue)["state"]) if tag != "present"),
)
_COLLECTIONS = ("sequence", *get_args(get_type_hints(CollectionValue)["kind"]))
_TEXT = ("string", "date", "datetime", "float", "integer", "decimal")


def _json(value):
    return cast(literal(value), JSONB())


def _members(value, *, ordinality=False):
    fn = func.jsonb_array_elements(value)
    field = column("value", JSONB())
    if ordinality:
        return fn.table_valued(field, with_ordinality="ordinal").render_derived()
    return fn.table_valued(field)


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
    return function(
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
    return function(
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
            If(kind == "array", (Return(func.jsonb_build_array("sequence", sequence)),)),
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


def data_operation_value_sql() -> str:
    value = core_variable("v", JSONB())
    domain = core_variable("domain", Text())
    key = core_variable("k", Text())
    body = Parameter("v", pg_type("jsonb"))
    members = _members(value[1])

    def digest(meaning):
        return func.encode(
            func.sha256(func.convert_to(func.data.canonical_json(meaning), "UTF8")), "hex"
        )

    def native_sql_function(schema, name, params, kind, expression):
        return sql_function(
            schema,
            name,
            parameters=params,
            returns=pg_type(kind),
            body=expression,
            volatility="immutable",
            strict=True,
            search_path=("pg_catalog", "pg_temp"),
        )

    return native_sql_script(
        (
            _field_guard(),
            _normalize(),
            _json_meaning(),
            native_sql_function(
                "data",
                "ddo_identity",
                (Parameter("domain", pg_type("text")), body),
                "text",
                select(
                    domain.op("||")(":").op("||")(
                        digest(
                            func.jsonb_build_array(
                                "ddo",
                                domain,
                                ENCODING_VERSION,
                                func.data.ddo_normalize(value),
                            )
                        )
                    ),
                ),
            ),
            native_sql_function("ops", "ddo_digest", (body,), "text", select(digest(value))),
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
    )
