"""Compile scalar binding semantics over the owned SourceValue codecs."""

from sqlalchemy import (
    Date,
    DateTime,
    Integer,
    Numeric,
    Text,
    case,
    cast,
    column,
    func,
    literal,
    or_,
    select,
)
from sqlalchemy.dialects.postgresql import JSONB, array

from .binding_primitives import BINDING_PRIMITIVE_ALIASES, BINDING_PRIMITIVES
from .native_program import (
    Assign,
    Block,
    If,
    Local,
    Parameter,
    Perform,
    Raise,
    Return,
    SelectInto,
    core_variable,
    function,
    pg_type,
)


def scalar_binding_native_sql():
    context = core_variable("context", JSONB())
    declared = core_variable("declared", Text())
    kind = core_variable("kind", Text())
    kind_row = core_variable("kind_row", JSONB())
    facts = core_variable("facts", JSONB())
    primitive = core_variable("primitive", Text())
    value = core_variable("value", JSONB())
    lexical = core_variable("lexical", Text())
    tag = core_variable("tag", Text())
    expected = core_variable("expected", Text())
    left = core_variable("left_value", JSONB())
    right = core_variable("right_value", JSONB())
    comparison = core_variable("comparison", Text())
    ordering = core_variable("ordering", Integer())
    left_numeric = core_variable("l", Numeric())
    right_numeric = core_variable("r", Numeric())
    object_ = func.pg_catalog.jsonb_build_array
    null_value = cast(literal("null"), JSONB())

    def routine(name, params, steps, *, returns="jsonb", locals_=(), strict=False):
        return function(
            "ops",
            name,
            parameters=tuple(Parameter(key, pg_type(type_)) for key, type_ in params),
            returns=pg_type(returns),
            body=Block(steps, locals_),
            strict=strict,
            volatility="immutable",
            search_path=("pg_catalog", "pg_temp"),
        )

    def check(condition, message, *, state="23514"):
        return If(condition, (Raise(message, state),))

    def scalar_text(value_):
        return value_.op("#>>", return_type=Text())(array([], type_=Text()))

    def normalize_tag(value_):
        return case(
            (value_.in_(("uri", "uriorcurie", "bytes")), "string"),
            (value_ == "double", "float"),
            else_=value_,
        )

    kinds = (
        func.jsonb_array_elements(context["model"]["kinds"])
        .table_valued(column("value", JSONB()))
        .render_derived(name="model_kind")
    )
    type_resolution = routine(
        "ddo_binding_type",
        (("context", "jsonb"), ("declared", "text")),
        (
            If(declared == "subject-context", (Return(declared),)),
            If(
                declared.like("primitive:%"),
                (Assign("primitive", func.substr(declared, 11)),),
                (
                    SelectInto(
                        select(kinds.c.value).where(
                            or_(
                                kinds.c.value["semantic_id"].astext == declared,
                                kinds.c.value["name"].astext == declared,
                            )
                        ),
                        ("kind_row",),
                    ),
                    check(
                        kind_row.is_(None), func.format("unknown native binding type %s", declared)
                    ),
                    Assign("facts", kind_row["facts"]["json"]),
                    Assign(
                        "primitive",
                        func.coalesce(
                            facts["primitive"].astext, facts["effective_primitive"].astext
                        ),
                    ),
                    If(
                        primitive.is_(None) & kind_row["category"].astext.in_(("class", "enum")),
                        (Assign("primitive", literal("string")),),
                    ),
                ),
            ),
            Assign("primitive", case(BINDING_PRIMITIVE_ALIASES, value=primitive, else_=primitive)),
            If(primitive.in_(BINDING_PRIMITIVES), (Return(primitive),)),
            Raise(func.format("unsupported native binding type %s", declared), "23514"),
        ),
        returns="text",
        locals_=(
            Local("kind_row", pg_type("jsonb")),
            Local("facts", pg_type("jsonb")),
            Local("primitive", pg_type("text")),
        ),
        strict=True,
    )
    scalar = routine(
        "ddo_binding_scalar",
        (("value", "jsonb"), ("kind", "text")),
        (
            check(or_(value.is_(None), value == null_value), "unknown or null binding operand"),
            If(kind.in_(("uri", "uriorcurie", "bytes")), (Assign("tag", literal("string")),)),
            If(kind == "double", (Assign("tag", literal("float")),)),
            If(
                tag.in_(("string", "date", "datetime", "float")),
                (
                    check(
                        func.jsonb_typeof(value) != "string",
                        "typed binding string representation required",
                    ),
                    Assign("lexical", scalar_text(value)),
                    If(tag == "float", (Perform(func.data.require_float_lexical(lexical)),)),
                    Return(func.data.ddo_normalize(object_(tag, lexical))),
                ),
                (
                    If(
                        tag == "boolean",
                        (
                            check(
                                func.jsonb_typeof(value) != "boolean",
                                "typed boolean operand required",
                            ),
                            Return(object_(tag, value)),
                        ),
                        (
                            If(
                                tag.in_(("integer", "decimal")),
                                (
                                    check(
                                        or_(
                                            func.jsonb_typeof(value) != "number",
                                            (tag == "integer")
                                            & (
                                                cast(scalar_text(value), Numeric())
                                                != func.trunc(cast(scalar_text(value), Numeric()))
                                            ),
                                        ),
                                        "typed numeric operand required",
                                    ),
                                    Return(
                                        func.data.ddo_normalize(object_(tag, scalar_text(value)))
                                    ),
                                ),
                                (If(tag == "json", (Return(object_("json", value)),)),),
                            ),
                        ),
                    ),
                ),
            ),
            Raise(
                func.format(
                    "unsupported native binding scalar type %s", func.coalesce(kind, "<NULL>")
                ),
                "23514",
            ),
        ),
        locals_=(Local("lexical", pg_type("text")), Local("tag", pg_type("text"), kind)),
    )

    def ordered(first, second):
        return case((first < second, -1), (first > second, 1), else_=0)

    compare = routine(
        "ddo_binding_compare",
        (("left_value", "jsonb"), ("right_value", "jsonb"), ("comparison", "text")),
        (
            If(
                or_(left[0].astext == "subject-context", right[0].astext == "subject-context"),
                (
                    check(
                        or_(
                            comparison != "equal",
                            left[0].astext.is_distinct_from("subject-context"),
                            right[0].astext.is_distinct_from("subject-context"),
                        ),
                        "context operands support equality only",
                        state="P0001",
                    ),
                    Return(left[1] == right[1]),
                ),
            ),
            check(tag.is_distinct_from(right[0].astext), "binding operand type mismatch"),
            If(
                comparison == "equal",
                (
                    If(
                        tag == "float",
                        (
                            Return(
                                func.ops.ddo_binding_float(left[1].astext)
                                == func.ops.ddo_binding_float(right[1].astext)
                            ),
                        ),
                    ),
                    Return(left == right),
                ),
            ),
            If(
                tag.in_(("integer", "decimal", "float")),
                (
                    Assign(
                        "l",
                        case(
                            (tag == "float", func.ops.ddo_binding_float(left[1].astext)),
                            else_=cast(left[1].astext, Numeric()),
                        ),
                    ),
                    Assign(
                        "r",
                        case(
                            (tag == "float", func.ops.ddo_binding_float(right[1].astext)),
                            else_=cast(right[1].astext, Numeric()),
                        ),
                    ),
                    Assign("ordering", ordered(left_numeric, right_numeric)),
                ),
                (
                    If(
                        tag == "date",
                        (
                            Assign(
                                "ordering",
                                ordered(
                                    cast(left[1].astext, Date()), cast(right[1].astext, Date())
                                ),
                            ),
                        ),
                        (
                            If(
                                tag == "datetime",
                                (
                                    Assign(
                                        "ordering",
                                        ordered(
                                            cast(left[1].astext, DateTime(timezone=True)),
                                            cast(right[1].astext, DateTime(timezone=True)),
                                        ),
                                    ),
                                ),
                                (
                                    If(
                                        tag == "string",
                                        (
                                            Assign(
                                                "ordering",
                                                ordered(
                                                    left[1].astext.collate("C"),
                                                    right[1].astext.collate("C"),
                                                ),
                                            ),
                                        ),
                                        (
                                            Raise(
                                                func.format(
                                                    "binding range does not support type %s",
                                                    func.coalesce(tag, "<NULL>"),
                                                ),
                                                "23514",
                                            ),
                                        ),
                                    ),
                                ),
                            ),
                        ),
                    ),
                ),
            ),
            If(
                comparison == "lower",
                (Return(ordering >= 0),),
                (If(comparison == "upper", (Return(ordering <= 0),)),),
            ),
            Raise("unsupported native binding comparison", "23514"),
        ),
        returns="bool",
        locals_=(
            Local("tag", pg_type("text"), left[0].astext),
            Local("l", pg_type("numeric")),
            Local("r", pg_type("numeric")),
            Local("ordering", pg_type("integer")),
        ),
        strict=True,
    )
    typed = routine(
        "ddo_binding_typed",
        (("value", "jsonb"), ("kind", "text")),
        (
            check(
                or_(value.is_(None), value[0].astext == "null"),
                "unknown or null typed binding operand",
            ),
            If(expected == "json", (Return(object_("json", func.data.ddo_json(value))),)),
            check(
                value[0].astext.is_distinct_from(expected),
                "native binding literal/field tag differs from admitted type",
            ),
            If(expected == "float", (Perform(func.data.require_float_lexical(value[1].astext)),)),
            Return(func.data.ddo_normalize(value)),
        ),
        locals_=(Local("expected", pg_type("text"), normalize_tag(kind)),),
    )
    return ";\n".join((type_resolution, scalar, compare, typed)) + ";\n"
