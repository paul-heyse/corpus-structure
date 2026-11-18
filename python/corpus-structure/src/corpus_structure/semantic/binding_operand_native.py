"""Compile model-bound binding operands and their declared parameter admission."""

from dataclasses import fields

from sqlalchemy import Boolean, Column, Text, cast, column, func, literal, or_, select
from sqlalchemy.dialects.postgresql import ARRAY, JSON, JSONB, aggregate_order_by, array

from .data_operation_model import SubjectContext
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
    SelectInto,
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


def binding_values_native_sql():
    """Evaluate frozen operands without reselecting products or physical aliases."""
    operand = core_variable("operand", JSONB())
    context = core_variable("context", JSONB())
    source = core_variable("source", Text())
    kind = core_variable("kind", Text())
    item = core_variable("item", JSONB())
    roledef = core_variable("roledef", JSONB())
    field = core_variable("field", JSONB())
    raw = core_variable("raw", JSONB())
    property_ = core_variable("property", JSONB())
    result = core_variable("result", JSONB())
    population = core_variable("population", JSONB())
    expected = core_variable("expected", Text())
    empty = cast(literal("[]"), JSONB())
    roledefs = _elements(context["roledefs"], "declared_role")
    kinds = _elements(context["model"]["kinds"], "declared_kind")
    members = _elements(func.coalesce(context["roles"][field["role"].astext], empty), "role_member")

    def collect(query, expression):
        return ForQuery(("item",), query, (Assign("result", result.concat(func.jsonb_build_array(expression))),))

    def values(value, *, typed=True):
        convert = func.ops.ddo_binding_typed if typed else func.ops.ddo_binding_scalar
        entries = _elements(value[1] if typed else value, "operand_item")
        is_sequence = value[0].astext == "sequence" if typed else func.jsonb_typeof(value) == "array"
        return If(is_sequence, (collect(select(entries.c.value), convert(item, kind)),), (
            Assign("result", func.jsonb_build_array(convert(value, kind))),
        ))

    context_record = func.jsonb_build_object(*(
        part for descriptor in fields(SubjectContext) for part in (
            descriptor.name,
            context[descriptor.name].astext if descriptor.name == "project_id" else (
                item[descriptor.name] if descriptor.name == "analyzed_scope" else item[descriptor.name].astext
            ),
        )
    ))
    routine = _routine("ddo_binding_values", (("operand", "jsonb"), ("context", "jsonb")), (
        If(source == "field", (
            Assign("field", operand["field"]),
            SelectInto(select(roledefs.c.value).where(roledefs.c.value["name"].astext == field["role"].astext), ("roledef",), strict=True),
            _check((field["projection"].astext != roledef["kind"].astext) & ~select(kinds.c.value).where((kinds.c.value["semantic_id"].astext == roledef["kind"].astext) & (kinds.c.value["name"].astext == field["projection"].astext)).exists(), "native binding projection differs from qualified role"),
            If(field["field"].astext.in_(("@product", "@member")), (
                Assign("kind", func.ops.ddo_binding_type(context, func.coalesce(operand["value_type"].astext, "primitive:string"))),
                _check(kind != "string", "native header binding field requires string type"),
                collect(select(members.c.value), func.ops.ddo_binding_scalar(item[func.substr(field["field"].astext, 2)], kind)),
                Return(result),
            )),
            If(field["field"].astext == "@context", (
                _check(or_(operand["value_type"].astext.is_distinct_from("subject-context"), func.nullif(context["project_id"].astext, "").is_(None)), "native qualified context lacks project/type"),
                collect(select(members.c.value), func.jsonb_build_array("subject-context", context_record)),
                Return(result),
            )),
            SelectInto(select(kinds.c.value).where(kinds.c.value["semantic_id"].astext == roledef["kind"].astext.concat("/property/").concat(field["field"].astext)), ("property",), strict=True),
            Assign("expected", property_["facts"]["json"]["range"].astext),
            Assign("kind", func.ops.ddo_binding_type(context, func.coalesce(operand["value_type"].astext, expected))),
            _check(operand.has_key("value_type") & (func.ops.ddo_binding_type(context, expected) != kind), "native binding field type differs"),
            ForQuery(("item",), select(members.c.value), (
                Assign("raw", func.data.ddo_field(item["meaning_body"], field["field"].astext)),
                Assign("result", result.concat(func.jsonb_build_array(func.ops.ddo_binding_typed(raw, kind)))),
            )),
            Return(result),
        )),
        Assign("kind", func.ops.ddo_binding_type(context, operand["value_type"].astext)),
        If(source == "literal", (
            Assign("raw", operand["value"]["json"]),
            _check(raw.is_(None), "missing typed native literal"),
            values(raw),
        ), (If(source == "parameter", (
            _check(~context["parameters"].has_key(operand["name"].astext), "missing frozen native binding parameter"),
            Assign("raw", func.data.ddo_field(context["parameter_meaning"], operand["name"].astext)),
            If(raw.is_not(None), (values(raw), Return(result))),
            _check(kind.in_(("float", "double")), "float demand parameter requires frozen typed meaning"),
            Assign("raw", context["parameters"][operand["name"].astext]),
            values(raw, typed=False),
        ), (If(source == "population", (
            Assign("population", context["populations"][operand["name"].astext]),
            _check(or_(population.is_(None), population["complete"].astext.is_distinct_from("true")), "binding membership population is not closed"),
            _check(func.coalesce(operand["population_projection"].astext, "member").is_distinct_from(func.coalesce(population["projection"].astext, "member")), "native population projection differs from frozen operand"),
            If(operand["population_projection"].astext == "qualified-context", (
                _check(kind != "subject-context", "native context population type differs"),
                collect(select(_elements(population["members"], "population_member").c.value), func.jsonb_build_array("subject-context", item)),
            ), (collect(select(_elements(population["members"], "population_member").c.value), func.ops.ddo_binding_scalar(item, kind)),)),
        ), (Raise(func.format("unsupported native binding operand %s", func.coalesce(source, "<NULL>")), "23514"),)),)),)),
        Return(result),
    ), locals_=(
        Local("source", pg_type("text"), operand["kind"].astext),
        *(Local(name, pg_type("text")) for name in ("kind", "expected")),
        *(Local(name, pg_type("jsonb")) for name in ("item", "roledef", "field", "raw", "property", "population")),
        Local("result", pg_type("jsonb"), empty),
    ))
    return routine + ";\n"
