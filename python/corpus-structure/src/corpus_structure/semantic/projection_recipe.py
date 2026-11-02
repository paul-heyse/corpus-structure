"""Finite resolved companion recipes shared by Core execution and projection analysis.

These nodes describe the selected application projections, not an arbitrary SQL language.
Public parameters, immutable preparation constants and private publication placement remain
different node kinds. Native wrappers resolve publication before supplying placement bindings.
"""

from __future__ import annotations

import re
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any, Literal, Never

from sqlalchemy import (
    BigInteger,
    Boolean,
    Double,
    Integer,
    Text,
    and_,
    bindparam,
    case,
    cast,
    func,
    literal,
    select,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.sql import ClauseElement, Select, visitors
from sqlalchemy.sql.type_api import TypeEngine

from .types import Diagnostic, PreparationError


@dataclass(frozen=True, slots=True)
class Parameter:
    name: str


@dataclass(frozen=True, slots=True)
class Field:
    source: str
    name: str


@dataclass(frozen=True, slots=True)
class Constant:
    value: str | int | bool | None


@dataclass(frozen=True, slots=True)
class ContextValue:
    name: Literal["projection_id", "families"]


@dataclass(frozen=True, slots=True)
class InternalBinding:
    name: Literal["published_build_id", "published_release_id"]


@dataclass(frozen=True, slots=True)
class JsonPath:
    value: Expression
    path: tuple[str | int, ...]
    as_text: bool


@dataclass(frozen=True, slots=True)
class Cast:
    value: Expression
    type_name: str


@dataclass(frozen=True, slots=True)
class Equal:
    left: Expression
    right: Expression


@dataclass(frozen=True, slots=True)
class All:
    values: tuple[Expression, ...]


@dataclass(frozen=True, slots=True)
class OneOf:
    value: Expression
    choices: ContextValue


@dataclass(frozen=True, slots=True)
class Conditional:
    when: Expression
    then: Expression
    otherwise: Expression


@dataclass(frozen=True, slots=True)
class HelperCall:
    helper: str
    arguments: tuple[Expression, ...]


type Expression = (
    Parameter
    | Field
    | Constant
    | ContextValue
    | InternalBinding
    | JsonPath
    | Cast
    | Equal
    | All
    | OneOf
    | Conditional
    | HelperCall
)


@dataclass(frozen=True, slots=True)
class ParameterDefinition:
    name: str
    native_name: str
    source: str
    sql_type: TypeEngine[Any]
    nullable: bool


@dataclass(frozen=True, slots=True)
class HelperDefinition:
    name: str
    function_name: str
    arguments: tuple[str, ...]
    result_source: str
    argument_types: tuple[TypeEngine[Any], ...]
    result_type: TypeEngine[Any]


@dataclass(frozen=True, slots=True)
class OutputField:
    name: str
    expression: Expression
    source: str
    role: str
    sql_type: TypeEngine[Any]
    nullable: bool


@dataclass(frozen=True, slots=True)
class SourceReference:
    name: str
    alias: str


@dataclass(frozen=True, slots=True)
class SourceDefinition:
    name: str
    relation: str | None
    input: SourceReference | None
    fields: tuple[OutputField, ...] = ()
    predicate: Expression | None = None
    materialized: bool = False


@dataclass(frozen=True, slots=True)
class JoinKey:
    left: Expression
    right: Expression


@dataclass(frozen=True, slots=True)
class Join:
    source: SourceReference
    keys: tuple[JoinKey, ...]
    relationship: str
    left_role: str
    right_role: str
    multiplicity: Literal["one_to_many", "many_to_one"]
    predicate: Expression | None = None


@dataclass(frozen=True, slots=True)
class Order:
    field: str
    collation: Literal["C"] | None = None


@dataclass(frozen=True, slots=True)
class ProjectionRecipe:
    family: str
    projection_id: str
    parameters: tuple[ParameterDefinition, ...]
    helpers: tuple[HelperDefinition, ...]
    sources: tuple[SourceDefinition, ...]
    source: SourceReference
    joins: tuple[Join, ...]
    fields: tuple[OutputField, ...]
    predicate: Expression
    order: tuple[Order, ...]
    families: tuple[str, ...]
    consumers: tuple[str, ...] = ()


def refuse(path: str, message: str) -> Never:
    raise PreparationError((Diagnostic("invalid_projection_recipe", path, message),))


def mapping(value: Any, path: str) -> dict[str, Any]:
    if not isinstance(value, dict) or not all(isinstance(key, str) for key in value):
        refuse(path, "expected a string-keyed recipe object")
    return value


def shape(
    value: Any, path: str, required: set[str], optional: set[str] | frozenset[str] = frozenset()
):
    value = mapping(value, path)
    if not required <= value.keys() or value.keys() - required - optional:
        refuse(path, "recipe fields differ from the supported shape")
    return value


def read_expression(value: Any, path: str) -> Expression:
    value = mapping(value, path)
    if len(value) != 1:
        refuse(path, "an expression requires exactly one operator")
    operator, body = next(iter(value.items()))
    if operator in {"parameter", "context", "internal", "cast"} and operator != "cast":
        if not isinstance(body, str):
            refuse(path, "expression name must be text")
        if operator == "parameter":
            return Parameter(body)
        if operator == "context" and body in {"projection_id", "families"}:
            return ContextValue(body)
        if operator == "internal" and body in {"published_build_id", "published_release_id"}:
            return InternalBinding(body)
        refuse(path, "unknown preparation context or internal binding")
    if operator == "field":
        if (
            not isinstance(body, list)
            or len(body) != 2
            or not all(isinstance(v, str) for v in body)
        ):
            refuse(path, "field requires a source alias and field name")
        return Field(*body)
    if operator == "constant":
        if body is not None and type(body) not in {str, int, bool}:
            refuse(path, "constant is not a supported exact scalar")
        return Constant(body)
    if operator in {"json", "json_text"}:
        body = shape(body, path, {"value", "path"})
        keys = body["path"]
        if not isinstance(keys, list) or not keys or any(type(k) not in {str, int} for k in keys):
            refuse(path, "JSON path requires nonempty exact string/integer members")
        return JsonPath(
            read_expression(body["value"], path + ".value"), tuple(keys), operator == "json_text"
        )
    if operator == "cast":
        body = shape(body, path, {"value", "type"})
        sql_type(body["type"], path)
        return Cast(read_expression(body["value"], path + ".value"), body["type"])
    if operator == "equal":
        if not isinstance(body, list) or len(body) != 2:
            refuse(path, "equality requires two operands")
        return Equal(*(read_expression(v, path + f".{i}") for i, v in enumerate(body)))
    if operator == "all":
        if not isinstance(body, list) or not body:
            refuse(path, "conjunction requires nonempty predicates")
        return All(tuple(read_expression(v, path + f".{i}") for i, v in enumerate(body)))
    if operator == "one_of":
        body = shape(body, path, {"value", "choices"})
        choices = read_expression(body["choices"], path + ".choices")
        if not isinstance(choices, ContextValue) or choices.name != "families":
            refuse(path, "only the declared companion-family set is supported")
        return OneOf(read_expression(body["value"], path + ".value"), choices)
    if operator == "case":
        body = shape(body, path, {"when", "then", "else"})
        return Conditional(
            *(read_expression(body[key], path + "." + key) for key in ("when", "then", "else"))
        )
    if operator == "call":
        body = shape(body, path, {"helper", "arguments"})
        if not isinstance(body["helper"], str) or not isinstance(body["arguments"], list):
            refuse(path, "helper requires a name and ordered arguments")
        return HelperCall(
            body["helper"],
            tuple(
                read_expression(v, path + f".arguments.{i}")
                for i, v in enumerate(body["arguments"])
            ),
        )
    return refuse(path, "unsupported expression operator: " + operator)


def sql_type(name: str, path: str = "projection") -> TypeEngine[Any]:
    types = {
        "text": Text,
        "bigint": BigInteger,
        "integer": Integer,
        "double": Double,
        "boolean": Boolean,
        "jsonb": JSONB,
    }
    if not isinstance(name, str) or name not in types:
        refuse(path, "unsupported explicit cast type")
    return types[name]()


def expression_fields(expression: Expression) -> tuple[Field, ...]:
    if isinstance(expression, Field):
        return (expression,)
    if isinstance(expression, (JsonPath, Cast)):
        children = (expression.value,)
    elif isinstance(expression, Equal):
        children = (expression.left, expression.right)
    elif isinstance(expression, All):
        children = expression.values
    elif isinstance(expression, OneOf):
        children = (expression.value,)
    elif isinstance(expression, Conditional):
        children = (expression.when, expression.then, expression.otherwise)
    elif isinstance(expression, HelperCall):
        children = expression.arguments
    else:
        children = ()
    return tuple(field for child in children for field in expression_fields(child))


def expression_type(expression: Expression, aliases, parameters, helpers, path: str):
    """Resolve names/type premises once; runtime lowerers consume only checked nodes."""

    def resolve(node):
        return expression_type(node, aliases, parameters, helpers, path)

    if isinstance(expression, Field):
        if expression.source not in aliases or expression.name not in aliases[expression.source]:
            refuse(path, "unknown source field: " + expression.source + "." + expression.name)
        return aliases[expression.source][expression.name]
    if isinstance(expression, Parameter):
        if expression.name not in parameters:
            refuse(path, "undeclared operation parameter: " + expression.name)
        return parameters[expression.name].sql_type
    if isinstance(expression, (ContextValue, InternalBinding)):
        return Text()
    if isinstance(expression, Constant):
        return (
            Boolean()
            if type(expression.value) is bool
            else BigInteger()
            if type(expression.value) is int
            else Text()
        )
    if isinstance(expression, JsonPath):
        if not isinstance(resolve(expression.value), JSONB):
            refuse(path, "JSON path requires a declared JSONB source")
        return Text() if expression.as_text else JSONB()
    if isinstance(expression, Cast):
        original = resolve(expression.value)
        target = sql_type(expression.type_name, path)
        if original._type_affinity is not target._type_affinity and not (
            isinstance(original, Text) and isinstance(target, (Integer, Boolean, Double))
        ):
            refuse(path, "unsupported or potentially lossy explicit coercion")
        return target
    if isinstance(expression, Equal):
        left, right = resolve(expression.left), resolve(expression.right)
        null_test = any(
            isinstance(value, Constant) and value.value is None
            for value in (expression.left, expression.right)
        )
        if not null_test and left._type_affinity is not right._type_affinity:
            refuse(path, "equality operands have incompatible declared types")
        return Boolean()
    if isinstance(expression, All):
        if any(not isinstance(resolve(value), Boolean) for value in expression.values):
            refuse(path, "conjunction requires Boolean predicates")
        return Boolean()
    if isinstance(expression, OneOf):
        if not isinstance(resolve(expression.value), Text):
            refuse(path, "family membership requires a text field")
        return Boolean()
    if isinstance(expression, Conditional):
        if not isinstance(resolve(expression.when), Boolean):
            refuse(path, "CASE requires a Boolean predicate")
        left, right = resolve(expression.then), resolve(expression.otherwise)
        if left._type_affinity is not right._type_affinity:
            refuse(path, "CASE branches have incompatible declared types")
        return left
    if isinstance(expression, HelperCall):
        if expression.helper not in helpers:
            refuse(path, "undeclared helper: " + expression.helper)
        helper = helpers[expression.helper]
        actual = tuple(resolve(arg) for arg in expression.arguments)
        if len(actual) != len(helper.argument_types) or any(
            a._type_affinity is not b._type_affinity
            for a, b in zip(actual, helper.argument_types, strict=True)
        ):
            refuse(path, "helper arguments differ from admitted signature")
        return helper.result_type
    return refuse(path, "unknown resolved expression")


def core_statement(recipe: ProjectionRecipe, metadata):
    """One executable Core tree. Native emission only substitutes declared variable bindings."""
    parameters = {p.name: bindparam(p.name, type_=p.sql_type) for p in recipe.parameters}
    helpers = {h.name: h for h in recipe.helpers}

    def lower(node: Expression, aliases):
        if isinstance(node, Parameter):
            return parameters[node.name]
        if isinstance(node, Field):
            return aliases[node.source].c[node.name]
        if isinstance(node, Constant):
            return literal(node.value)
        if isinstance(node, ContextValue):
            return (
                literal(recipe.projection_id) if node.name == "projection_id" else recipe.families
            )
        if isinstance(node, InternalBinding):
            return bindparam("_" + node.name, type_=Text())
        if isinstance(node, JsonPath):
            value = lower(node.value, aliases)
            result = value[node.path[0] if len(node.path) == 1 else node.path]
            return result.astext if node.as_text else result
        if isinstance(node, Cast):
            return cast(lower(node.value, aliases), sql_type(node.type_name))
        if isinstance(node, Equal):
            return lower(node.left, aliases) == lower(node.right, aliases)
        if isinstance(node, All):
            return and_(*(lower(value, aliases) for value in node.values))
        if isinstance(node, OneOf):
            return lower(node.value, aliases).in_(recipe.families)
        if isinstance(node, Conditional):
            return case(
                (lower(node.when, aliases), lower(node.then, aliases)),
                else_=lower(node.otherwise, aliases),
            )
        if isinstance(node, HelperCall):
            helper = helpers[node.helper]
            function = func
            for part in helper.function_name.split("."):
                function = getattr(function, part)
            return function(
                *(lower(value, aliases) for value in node.arguments), type_=helper.result_type
            )
        raise TypeError("unchecked projection expression")

    sources = {}
    for source in recipe.sources:
        if source.relation is not None:
            sources[source.name] = metadata.tables[source.relation]
        else:
            assert source.input is not None and source.predicate is not None
            base = sources[source.input.name].alias(source.input.alias)
            aliases = {source.input.alias: base}
            statement = (
                select(
                    *(
                        cast(lower(f.expression, aliases), f.sql_type).label(f.name)
                        for f in source.fields
                    )
                )
                .select_from(base)
                .where(lower(source.predicate, aliases))
            )
            cte = statement.cte(source.name)
            sources[source.name] = cte.prefix_with("MATERIALIZED") if source.materialized else cte
    source = sources[recipe.source.name].alias(recipe.source.alias)
    aliases = {recipe.source.alias: source}
    for join in recipe.joins:
        target = sources[join.source.name].alias(join.source.alias)
        aliases[join.source.alias] = target
        on = [lower(Equal(key.left, key.right), aliases) for key in join.keys]
        if join.predicate is not None:
            on.append(lower(join.predicate, aliases))
        source = source.join(target, and_(*on))
    fields = {
        f.name: cast(lower(f.expression, aliases), f.sql_type).label(f.name) for f in recipe.fields
    }
    statement = select(*fields.values()).select_from(source).where(lower(recipe.predicate, aliases))
    return statement.order_by(
        *(
            fields[o.field].collate(o.collation) if o.collation else fields[o.field]
            for o in recipe.order
        )
    )


def native_statement(
    statement: Select,
    recipe: ProjectionRecipe,
    *,
    internal_bindings: Mapping[str, str] | None = None,
) -> Select:
    from sqlalchemy import literal_column
    from sqlalchemy.sql.elements import BindParameter

    variables = {p.name: (p.native_name, p.sql_type) for p in recipe.parameters}
    variables["_published_build_id"] = ("published.build_id", Text())
    variables["_published_release_id"] = ("published.release_id", Text())
    for name, value in (internal_bindings or {}).items():
        if (
            name not in {"_published_build_id", "_published_release_id"}
            or re.fullmatch(r"[a-z][a-z0-9_]*", value) is None
        ):
            raise ValueError("unsupported native internal binding")
        variables[name] = (value, Text())

    def replace(element: ClauseElement, **kw: Any) -> ClauseElement | None:
        if isinstance(element, BindParameter) and element.key in variables:
            name, typ = variables[element.key]
            return literal_column(name, type_=typ)
        return None

    result = visitors.replacement_traverse(statement, {}, replace)
    if not isinstance(result, Select):
        raise TypeError("native projection lowering must retain the Core SELECT")
    return result
