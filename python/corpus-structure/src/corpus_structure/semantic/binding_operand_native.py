"""Compile model-bound binding operands and their declared parameter admission."""

from sqlalchemy import Boolean, Column, Text, cast, column, func, literal, or_, select
from sqlalchemy.dialects.postgresql import ARRAY, JSON, JSONB, aggregate_order_by, array

from .native_program import (
    Assign,
    Block,
    Continue,
    ForQuery,
    If,
    Local,
    Parameter,
    Perform,
    Raise,
    Return,
    column_type,
    core_variable,
    function,
    pg_type,
)


def _elements(value, name="entry"):
    return func.jsonb_array_elements(value).table_valued(column("value", JSONB())).render_derived(name=name)


def _entries(value, name="entry"):
    return func.jsonb_each(value).table_valued(column("key", Text()), column("value", JSONB())).render_derived(name=name)


def _routine(name, parameters, steps, *, returns=None, locals_=()):
    return function(
        "ops", name,
        parameters=tuple(Parameter(key, pg_type(type_)) for key, type_ in parameters),
        returns=returns or pg_type("jsonb"), body=Block(steps, locals_),
        strict=True, volatility="immutable", search_path=("pg_catalog", "pg_temp"),
    )


def _check(condition, message):
    return If(condition, (Raise(message, "P0001"),))


def binding_parameter_native_sql():
    node = core_variable("node", JSONB())
    names = core_variable("names", ARRAY(Text()))
    item = core_variable("item", JSONB())
    child = core_variable("child", JSONB())
    empty = cast(literal("[]"), JSONB())
    scalar = item.op("#>>", return_type=Text())(array([], type_=Text()))
    role_nodes = _elements(func.coalesce(node["roles"], empty), "role_node")
    fields = _elements(func.coalesce(node["fields"], empty), "field_node")
    operands = _elements(func.coalesce(node["operands"], empty), "operand_node")
    children = _elements(func.coalesce(node["children"], empty), "child_node")
    unique_names = func.unnest(names).table_valued(column("value", Text())).render_derived(name="role_name")
    roles = _routine("ddo_binding_roles", (("node", "jsonb"),), (
        ForQuery(("item",), select(role_nodes.c.value), (Assign("names", func.array_append(names, scalar)),)),
        ForQuery(("item",), select(fields.c.value), (Assign("names", func.array_append(names, item["role"].astext)),)),
        ForQuery(("item",), select(operands.c.value).where(operands.c.value["kind"].astext == "field"), (Assign("names", func.array_append(names, item["field"]["role"].astext)),)),
        ForQuery(("child",), select(children.c.value), (Assign("names", names.concat(func.ops.ddo_binding_roles(child))),)),
        Return(select(func.coalesce(func.array_agg(aggregate_order_by(unique_names.c.value.distinct(), unique_names.c.value)), array([], type_=Text()))).scalar_subquery()),
    ), returns=column_type(Column("roles", ARRAY(Text()))), locals_=(
        Local("names", column_type(Column("roles", ARRAY(Text()))), array([], type_=Text())),
        Local("item", pg_type("jsonb")), Local("child", pg_type("jsonb")),
    ))

    operation = core_variable("operation", JSONB())
    selection = core_variable("selection", JSONB())
    model = core_variable("model", JSONB())
    definitions = core_variable("definitions", JSONB())
    name = core_variable("name", Text())
    definition = core_variable("definition", JSONB())
    value = core_variable("value", JSONB())
    kind = core_variable("kind", Text())
    declared = _entries(definitions, "declared")
    selected = _entries(selection["parameters"], "selected")
    items = _elements(value[1], "parameter_item")
    validate = _routine("ddo_validate_parameters", (("operation", "jsonb"), ("selection", "jsonb"), ("model", "jsonb")), (
        _check(or_(func.jsonb_typeof(selection["parameters"]).is_distinct_from("object"), selection["parameter_meaning"].is_(None), func.data.ddo_json(func.data.ddo_normalize(selection["parameter_meaning"])).is_distinct_from(selection["parameters"])), "frozen parameter display differs from exact typed meaning"),
        _check(select(declared.c.key).where(declared.c.value.has_key("kind")).exists() & select(selected.c.key).where(~definitions.has_key(selected.c.key)).exists(), "undeclared frozen nominal operation parameter"),
        ForQuery(("name", "definition"), select(declared.c.key, declared.c.value), (
            If(~or_(definition.has_key("kind"), definition.has_key("value_type")), (Continue(),)),
            If(~selection["parameters"].has_key(name), (
                _check(or_(definition.has_key("default"), func.coalesce(definition["required"].astext, "true") == "true"), func.format("missing frozen demand parameter %s", name)),
                Continue(),
            )),
            Assign("value", func.data.ddo_field(selection["parameter_meaning"], name)),
            If(definition.has_key("kind"), (
                _check(or_(func.jsonb_typeof(definition["body_schema"]).is_distinct_from("object"), func.jsonb_typeof(definition["meaning_schema"]).is_distinct_from("object"), ~func.public.json_matches_schema(cast(definition["body_schema"], JSON()), cast(selection["parameters"][name], JSON()), type_=Boolean()), ~func.public.json_matches_schema(cast(definition["meaning_schema"], JSON()), cast(value, JSON()), type_=Boolean())), func.format("nominal frozen parameter violates captured schema: %s", name)),
            ), (
                Assign("kind", func.ops.ddo_binding_type(func.jsonb_build_object("model", model), definition["value_type"].astext)),
                If(func.coalesce(definition["many"].astext, "false") == "true", (
                    _check(value[0].astext.is_distinct_from("sequence"), "frozen parameter must be a typed sequence"),
                    ForQuery(("item",), select(items.c.value), (Perform(func.ops.ddo_binding_typed(item, kind)),)),
                ), (Perform(func.ops.ddo_binding_typed(value, kind)),)),
            )),
        )),
    ), returns=pg_type("void"), locals_=(
        Local("definitions", pg_type("jsonb"), operation["parameters"]["json"]),
        Local("name", pg_type("text")), Local("definition", pg_type("jsonb")),
        Local("value", pg_type("jsonb")), Local("item", pg_type("jsonb")), Local("kind", pg_type("text")),
    ))
    return ";\n".join((roles, validate)) + ";\n"
