"""Prepared SQLGlot analysis derived directly from the checked companion recipe.

Core remains execution authority. This product describes query dependencies, not native
permission, arbitrary helper behavior, scientific provenance or semantic equivalence.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from functools import lru_cache
from hashlib import sha256
from typing import Literal

import sqlglot
from sqlalchemy.dialects.postgresql import dialect
from sqlglot import exp
from sqlglot.lineage import lineage
from sqlglot.optimizer.annotate_types import annotate_types
from sqlglot.optimizer.qualify import qualify
from sqlglot.optimizer.scope import build_scope
from sqlglot.schema import MappingSchema

from . import projection_recipe as ir
from .determinants import analysis_runtime
from .identity import canonical_bytes
from .refusals import SemanticRefusal


@dataclass(frozen=True)
class ProjectionDependencyOccurrence:
    identity: str
    structural_path: str
    role: Literal["value", "membership", "ordering", "unknown"]
    clause: str
    source_ref: str
    target_ref: str
    output: str | None = None
    relationship: str | None = None
    unknown_reason: str | None = None


@dataclass(frozen=True)
class ProjectionAnalysis:
    projection_id: str
    profile: str
    library_version: str
    consumers: tuple[str, ...]
    output_origins: tuple[tuple[str, str], ...]
    output_types: tuple[tuple[str, str], ...]
    value_dependencies: tuple[tuple[str, tuple[str, ...]], ...]
    relational_sources: tuple[str, ...]
    relational_dependencies: tuple[tuple[str, tuple[str, ...]], ...]
    expressions: tuple[tuple[str, str], ...]
    relationships: tuple[str, ...]
    helpers: tuple[str, ...]
    unknowns: tuple[str, ...]
    logical_sources: tuple[tuple[str, str], ...]
    occurrences: tuple[ProjectionDependencyOccurrence, ...] = ()
    detail_status: Literal["available", "unavailable"] = "unavailable"


class ProjectionAnalysisUnavailable(SemanticRefusal):
    """The selected analysis cannot faithfully represent this required recipe."""

    def __init__(self, message: str, *, model_path: str = "projection"):
        self.model_path = model_path
        super().__init__(message)


def _dtype(typ) -> exp.DataType:
    return exp.DataType.build(str(typ.compile(dialect=dialect())), dialect="postgres")


def _incomplete_type(typ: exp.DataType) -> bool:
    return typ.this in {exp.DType.UNKNOWN, exp.DType.USERDEFINED} or (
        typ.this in {exp.DType.ARRAY, exp.DType.MAP, exp.DType.STRUCT} and not typ.expressions
    )


def expand_sources(
    query: exp.Expr,
    sources: Mapping[str, exp.Expr],
    *,
    physical_sources: frozenset[str],
    parameters: frozenset[str] = frozenset(),
) -> exp.Query:
    """Expand a finite model-pinned closure; stored/materialized sources are barriers.

    SQLGlot recursively expands without cycle or CTE-shadow checks. Establish those
    premises before calling it, retaining the caller's model-origin annotated trees.
    """
    if not isinstance(query, exp.Query):
        raise ProjectionAnalysisUnavailable("<projection>: source is not a supported query")
    query_sources: dict[str, exp.Query] = {}
    for name, source in sources.items():
        if not isinstance(source, exp.Query):
            raise ProjectionAnalysisUnavailable(f"{name}: source is not a supported query")
        query_sources[name] = source
    edges = {}
    for name, tree in (("<projection>", query), *query_sources.items()):
        ctes = [cte.alias for cte in tree.find_all(exp.CTE)]
        if len(set(ctes)) != len(ctes) or set(ctes) & sources.keys():
            raise ProjectionAnalysisUnavailable(f"{name}: ambiguous local CTE/source collision")
        for node in tree.walk():
            if isinstance(node, exp.Command) or node.error_messages():
                raise ProjectionAnalysisUnavailable(f"{name}: opaque or malformed query structure")
            if isinstance(node, exp.Placeholder) and (
                node.name not in parameters or node.type is None
            ):
                raise ProjectionAnalysisUnavailable(f"{name}: unresolved placeholder {node.name}")
            if isinstance(node, exp.Anonymous) and (
                not node.meta.get("model_source") or node.type is None
            ):
                raise ProjectionAnalysisUnavailable(f"{name}: unbound helper {node.name}")
            if isinstance(node, exp.DataType) and _incomplete_type(node):
                raise ProjectionAnalysisUnavailable(
                    f"{name}: incomplete declared type {node.sql()}"
                )
        references = {
            ".".join(filter(None, (table.db, table.name)))
            for table in tree.find_all(exp.Table)
            if table.db or table.name not in ctes
        }
        missing = references - sources.keys() - physical_sources
        if missing:
            raise ProjectionAnalysisUnavailable(f"{name}: missing source {sorted(missing)}")
        edges[name] = references & sources.keys()
    done, active = set(), set()

    def visit(name):
        if name in active:
            raise ProjectionAnalysisUnavailable(f"{name}: cyclic pinned source closure")
        if name in done:
            return
        active.add(name)
        for child in edges[name]:
            visit(child)
        active.remove(name)
        done.add(name)

    for name in edges:
        visit(name)
    result = exp.expand(query, dict(query_sources), dialect="postgres", copy=True)
    if not isinstance(result, exp.Query):
        raise ProjectionAnalysisUnavailable("expanded projection is not a query")
    return result


def recipe_expression(recipe: ir.ProjectionRecipe) -> exp.Select:
    parameters = {item.name: item for item in recipe.parameters}
    helpers = {item.name: item for item in recipe.helpers}

    def lower(node: ir.Expression) -> exp.Expr:
        match node:
            case ir.Parameter(name):
                result = exp.Placeholder(this=name)
                result.type = _dtype(parameters[name].sql_type)
                return result
            case ir.InternalBinding(name):
                if name not in {"published_build_id", "published_release_id"}:
                    raise ProjectionAnalysisUnavailable(f"unknown internal binding: {name}")
                result = exp.Placeholder(this=name)
                result.type = exp.DataType.build("TEXT")
                return result
            case ir.Field(source, name):
                return exp.column(name, table=source)
            case ir.Constant(value):
                return exp.convert(value)
            case ir.ContextValue("projection_id"):
                return exp.convert(recipe.projection_id)
            case ir.JsonPath(value, path, as_text):
                result = lower(value)
                for position, part in enumerate(path):
                    cls = (
                        exp.JSONBExtractScalar
                        if as_text and position == len(path) - 1
                        else exp.JSONBExtract
                    )
                    result = cls(this=result, expression=exp.convert(part))
                return result
            case ir.Cast(value, type_name):
                return exp.Cast(
                    this=lower(value), to=exp.DataType.build(type_name, dialect="postgres")
                )
            case ir.Equal(left, right):
                return exp.EQ(this=lower(left), expression=lower(right))
            case ir.All(values):
                return exp.and_(*(lower(value) for value in values))
            case ir.OneOf(value, ir.ContextValue("families")):
                return exp.In(
                    this=lower(value), expressions=[exp.convert(v) for v in recipe.families]
                )
            case ir.Conditional(when, then, otherwise):
                return exp.Case(
                    ifs=[exp.If(this=lower(when), true=lower(then))], default=lower(otherwise)
                )
            case ir.HelperCall(helper, arguments):
                definition = helpers[helper]
                if len(arguments) != len(definition.arguments):
                    raise ProjectionAnalysisUnavailable(f"helper arity differs: {helper}")
                result = exp.Anonymous(
                    this=definition.function_name, expressions=[lower(a) for a in arguments]
                )
                result.type = _dtype(definition.result_type)
                result.meta["model_source"] = definition.result_source
                return result
            case _:
                raise ProjectionAnalysisUnavailable(
                    f"unsupported recipe node: {type(node).__name__}"
                )

    sources = {source.name: source for source in recipe.sources}

    def reference(source: ir.SourceReference) -> exp.Table:
        definition = sources[source.name]
        parts = (definition.relation or definition.name).split(".")
        if len(parts) not in (1, 2):
            raise ProjectionAnalysisUnavailable("source requires declared schema/relation identity")
        return exp.Table(
            this=exp.to_identifier(parts[-1]),
            db=exp.to_identifier(parts[0]) if len(parts) == 2 else None,
            alias=exp.TableAlias(this=exp.to_identifier(source.alias)),
        )

    def outputs(fields: tuple[ir.OutputField, ...]):
        result = []
        for field in fields:
            value = exp.Cast(this=lower(field.expression), to=_dtype(field.sql_type))
            value.meta.update(model_source=field.source, model_member=field.name)
            result.append(exp.Alias(this=value, alias=exp.to_identifier(field.name)))
        return result

    query = exp.select(*outputs(recipe.fields)).from_(reference(recipe.source))
    for join in recipe.joins:
        conditions: list[exp.Expr] = [
            exp.EQ(this=lower(k.left), expression=lower(k.right)) for k in join.keys
        ]
        if join.predicate is not None:
            conditions.append(lower(join.predicate))
        query = query.join(reference(join.source), on=exp.and_(*conditions))
    query = query.where(lower(recipe.predicate))
    for order in recipe.order:
        value = exp.column(order.field)
        if order.collation is not None:
            value = exp.Collate(this=value, expression=exp.to_identifier(order.collation))
        query = query.order_by(value)
    ctes = []
    query_sources = {}
    for source in recipe.sources:
        if source.relation is not None:
            continue
        if source.input is None:
            raise ProjectionAnalysisUnavailable(f"derived source lacks input: {source.name}")
        body = exp.select(*outputs(source.fields)).from_(reference(source.input))
        if source.predicate is not None:
            body = body.where(lower(source.predicate))
        if not source.materialized:
            body.meta["model_source"] = "projection:" + recipe.family + "/sources/" + source.name
            query_sources[source.name] = body
            continue
        ctes.append(
            exp.CTE(
                this=body,
                alias=exp.TableAlias(this=exp.to_identifier(source.name)),
                materialized=source.materialized,
            )
        )
    if ctes:
        query.set("with_", exp.With(expressions=ctes))
    expanded = expand_sources(
        query,
        query_sources,
        physical_sources=frozenset(s.relation for s in recipe.sources if s.relation is not None),
        parameters=frozenset(parameters) | {"published_build_id", "published_release_id"},
    )
    if not isinstance(expanded, exp.Select):
        raise ProjectionAnalysisUnavailable("expanded recipe must retain its SELECT")
    return expanded


def dependency_occurrences(
    recipe: ir.ProjectionRecipe,
) -> tuple[ProjectionDependencyOccurrence, ...]:
    """Inventory checked structural uses before SQLGlot can merge equal expressions.

    Derived definitions are visited once and uses retain local edges. This is not
    path enumeration or an assertion about the body of a native helper.
    """
    sources = {item.name: item for item in recipe.sources}
    helpers = {item.name: item for item in recipe.helpers}
    reachable = set()

    def include(name):
        if name in reachable:
            return
        reachable.add(name)
        selected = sources[name]
        if selected.input is not None:
            include(selected.input.name)

    include(recipe.source.name)
    for join in recipe.joins:
        include(join.source.name)
    result = []
    base = "projection:" + recipe.family

    def emit(path, role, clause, source, target, output=None, relationship=None, reason=None):
        identity = (
            "projection-occurrence:"
            + sha256(
                canonical_bytes((recipe.projection_id, path, role, source, target, relationship))
            ).hexdigest()
        )
        result.append(
            ProjectionDependencyOccurrence(
                identity, path, role, clause, source, target, output, relationship, reason
            )
        )

    def walk(node, path, role, clause, target, aliases, output=None, relationship=None):
        if isinstance(node, ir.Field):
            definition = sources.get(aliases.get(node.source, ""))
            if definition is None or node.name not in {f.name for f in definition.fields}:
                raise ProjectionAnalysisUnavailable("missing checked source field: " + path)
            source = (
                "physical:" + definition.relation + "." + node.name
                if definition.relation
                else base + "/sources/" + definition.name + "/fields/" + node.name
            )
            emit(path, role, clause, source, target, output, relationship)
            return
        if isinstance(node, ir.Parameter):
            parameter = next((p for p in recipe.parameters if p.name == node.name), None)
            if parameter is None:
                raise ProjectionAnalysisUnavailable("missing checked parameter: " + path)
            emit(path, role, clause, "parameter:" + node.name, target, output, relationship)
            return
        if isinstance(node, ir.HelperCall):
            helper = helpers[node.helper]
            emit(
                path + "/body",
                "unknown",
                clause,
                helper.result_source,
                target,
                output,
                relationship,
                "helper body not analyzed: " + helper.function_name,
            )
            children = [("arguments/" + str(i), value) for i, value in enumerate(node.arguments)]
        elif isinstance(node, (ir.JsonPath, ir.Cast, ir.OneOf)):
            children = [("value", node.value)]
        elif isinstance(node, ir.Equal):
            children = [("left", node.left), ("right", node.right)]
        elif isinstance(node, ir.All):
            children = [("values/" + str(i), value) for i, value in enumerate(node.values)]
        elif isinstance(node, ir.Conditional):
            children = [("when", node.when), ("then", node.then), ("otherwise", node.otherwise)]
        elif isinstance(node, (ir.Constant, ir.ContextValue, ir.InternalBinding)):
            children = []
        else:
            raise ProjectionAnalysisUnavailable("unsupported occurrence node: " + path)
        for suffix, child in children:
            walk(child, path + "/" + suffix, role, clause, target, aliases, output, relationship)

    aliases = {
        recipe.source.alias: recipe.source.name,
        **{j.source.alias: j.source.name for j in recipe.joins},
    }
    for field in recipe.fields:
        if not field.source:
            raise ProjectionAnalysisUnavailable("missing checked output origin: " + field.name)
        path = base + "/fields/" + field.name
        walk(field.expression, path, "value", "output", path, aliases, field.name)
    walk(recipe.predicate, base + "/where", "membership", "where", base + "/where", aliases)
    for index, join in enumerate(recipe.joins):
        path = base + "/joins/" + str(index)
        for key_index, key in enumerate(join.keys):
            for side in ("left", "right"):
                walk(
                    getattr(key, side),
                    path + "/keys/" + str(key_index) + "/" + side,
                    "membership",
                    "join",
                    path,
                    aliases,
                    relationship=join.relationship,
                )
        if join.predicate is not None:
            walk(
                join.predicate,
                path + "/predicate",
                "membership",
                "join",
                path,
                aliases,
                relationship=join.relationship,
            )
    by_output = {field.name: field for field in recipe.fields}
    for index, order in enumerate(recipe.order):
        field = by_output.get(order.field)
        if field is None:
            raise ProjectionAnalysisUnavailable("missing ordered output: " + order.field)
        path = base + "/order/" + str(index)
        walk(field.expression, path, "ordering", "order", path, aliases, field.name)
    for source in recipe.sources:
        if source.relation is not None or source.name not in reachable:
            continue
        if source.input is None:
            raise ProjectionAnalysisUnavailable("derived source lacks input: " + source.name)
        local = {source.input.alias: source.input.name}
        for field in source.fields:
            path = base + "/sources/" + source.name + "/fields/" + field.name
            walk(field.expression, path, "value", "source", path, local)
        if source.predicate is not None:
            path = base + "/sources/" + source.name + "/where"
            walk(source.predicate, path, "membership", "where", path, local)
    return tuple(result)


def occurrence_summaries(recipe, occurrences):
    """Compact physical summaries project the same local occurrence authority."""
    definitions = {}
    for item in occurrences:
        if item.clause == "source" and item.role == "value":
            definitions.setdefault(item.target_ref, []).append(item.source_ref)

    def leaves(reference, trail=()):
        if reference.startswith("physical:"):
            return {reference}
        if reference in trail:
            raise ProjectionAnalysisUnavailable("cyclic occurrence source definition")
        return {
            leaf
            for child in definitions.get(reference, ())
            for leaf in leaves(child, (*trail, reference))
        }

    values = {field.name: set() for field in recipe.fields}
    relations = {}
    for item in occurrences:
        if item.role == "value" and item.clause == "output":
            values[item.output].update(leaves(item.source_ref))
        elif item.role in {"membership", "ordering"}:
            relations.setdefault(item.clause, set()).update(leaves(item.source_ref))
    return (
        tuple((name, tuple(sorted(fields))) for name, fields in values.items()),
        tuple((name, tuple(sorted(fields))) for name, fields in sorted(relations.items())),
    )


def analyze_recipe(recipe: ir.ProjectionRecipe) -> ProjectionAnalysis:
    return _analyze_recipe_cached(recipe, analysis_runtime())


@lru_cache(maxsize=32)
def _analyze_recipe_cached(
    recipe: ir.ProjectionRecipe, runtime: tuple[tuple[str, str], ...]
) -> ProjectionAnalysis:
    """Prepare analysis once for a checked immutable projection at its valid lifetime."""
    schema = MappingSchema(dialect="postgres")
    physical_sources = set()
    for source in recipe.sources:
        if source.relation is not None:
            physical_sources.add(source.relation)
            schema.add_table(
                source.relation, {field.name: _dtype(field.sql_type) for field in source.fields}
            )
    query = recipe_expression(recipe)
    if any(isinstance(node, exp.Command) for node in query.walk()):
        raise ProjectionAnalysisUnavailable("opaque command cannot establish projection analysis")
    qualified = qualify(query, schema=schema, dialect="postgres", validate_qualify_columns=True)
    annotate_types(qualified, schema=schema, dialect="postgres", overwrite_types=False)
    scope = build_scope(qualified)
    if scope is None:
        raise ProjectionAnalysisUnavailable("projection has no supported query scope")
    nodes = lineage(None, qualified, schema=schema, scope=scope, dialect="postgres")
    if not isinstance(nodes, dict):
        raise ProjectionAnalysisUnavailable("expected all named output lineage")
    expected_origins = {field.name: field.source for field in recipe.fields}
    if len(expected_origins) != len(recipe.fields) or set(nodes) != expected_origins.keys():
        raise ProjectionAnalysisUnavailable(
            "named output lineage differs from required model fields"
        )
    expressions = [
        (
            f"projection:{recipe.family}/fields/{value.alias_or_name}",
            value.this.sql(dialect="postgres"),
        )
        for value in qualified.selects
    ]
    for scope_index, selected_scope in enumerate(scope.traverse()):
        expression = selected_scope.expression
        clauses = [(kind, expression.args.get(kind)) for kind in ("where", "group", "order")]
        clauses += [("join", join.args.get("on")) for join in expression.args.get("joins", ())]
        for kind, clause in clauses:
            if clause is None:
                continue
            expressions.append(
                (
                    f"projection:{recipe.family}/scope/{scope_index}/{kind}",
                    clause.sql(dialect="postgres"),
                )
            )
    types = tuple(
        (value.alias_or_name, value.type.sql(dialect="postgres") if value.type else "UNKNOWN")
        for value in qualified.selects
    )
    unknowns = [f"unknown output type: {name}" for name, typ in types if typ == "UNKNOWN"]
    for node in qualified.walk():
        if isinstance(node, exp.DataType) and any(
            _incomplete_type(value) for value in node.walk() if isinstance(value, exp.DataType)
        ):
            unknowns.append("incomplete declared type: " + node.sql(dialect="postgres"))
    for field in recipe.fields:
        if not field.source:
            unknowns.append("missing output model origin: " + field.name)
    for value in qualified.selects:
        if value.this.meta.get("model_source") != expected_origins[value.alias_or_name]:
            raise ProjectionAnalysisUnavailable(
                "transformed output model origin differs from checked recipe: "
                + value.alias_or_name
            )
    unknowns.extend(
        "helper body not analyzed: " + helper.function_name for helper in recipe.helpers
    )
    occurrences = dependency_occurrences(recipe)
    dependencies, relational_dependencies = occurrence_summaries(recipe, occurrences)
    return ProjectionAnalysis(
        recipe.projection_id,
        "companion-query-analysis-3",
        sqlglot.__version__,
        recipe.consumers,
        tuple((field.name, field.source) for field in recipe.fields),
        types,
        tuple(dependencies),
        tuple(
            sorted(
                {
                    table.db + "." + table.name
                    for table in qualified.find_all(exp.Table)
                    if table.db + "." + table.name in physical_sources
                }
            )
        ),
        relational_dependencies,
        tuple(expressions),
        tuple(join.relationship for join in recipe.joins),
        tuple(helper.function_name for helper in recipe.helpers),
        tuple(unknowns),
        tuple(
            (source.name, f"projection:{recipe.family}/sources/{source.name}")
            for source in recipe.sources
            if source.relation is None
        ),
        occurrences,
        "available",
    )
