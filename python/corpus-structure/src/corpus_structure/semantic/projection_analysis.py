"""Prepared SQLGlot analysis derived directly from the checked companion recipe.

Core remains execution authority. This product describes query dependencies, not native
permission, arbitrary helper behavior, scientific provenance or semantic equivalence.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from functools import lru_cache

import sqlglot
from sqlalchemy.dialects.postgresql import dialect
from sqlglot import exp
from sqlglot.lineage import lineage
from sqlglot.optimizer.annotate_types import annotate_types
from sqlglot.optimizer.qualify import qualify
from sqlglot.optimizer.scope import build_scope
from sqlglot.schema import MappingSchema

from . import projection_recipe as ir
from .metadata import metadata
from .refusals import SemanticRefusal


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
    query: exp.Query,
    sources: Mapping[str, exp.Query],
    *,
    physical_sources: frozenset[str],
    parameters: frozenset[str] = frozenset(),
) -> exp.Query:
    """Expand a finite model-pinned closure; stored/materialized sources are barriers.

    SQLGlot recursively expands without cycle or CTE-shadow checks. Establish those
    premises before calling it, retaining the caller's model-origin annotated trees.
    """
    edges = {}
    for name, tree in (("<projection>", query), *sources.items()):
        if not isinstance(tree, exp.Query):
            raise ProjectionAnalysisUnavailable(f"{name}: source is not a supported query")
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
    result = exp.expand(query, dict(sources), dialect="postgres", copy=True)
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


@lru_cache(maxsize=32)
def analyze_recipe(recipe: ir.ProjectionRecipe) -> ProjectionAnalysis:
    """Prepare analysis once for a checked immutable projection at its valid lifetime."""
    schema = MappingSchema(dialect="postgres")
    for source in recipe.sources:
        if source.relation is not None:
            relation = metadata.tables[source.relation]
            schema.add_table(source.relation, {c.name: _dtype(c.type) for c in relation.columns})
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
    dependencies = []
    for name, root in nodes.items():
        leaves = set()
        for node in root.walk():
            if isinstance(node.expression, exp.Table):
                table = node.expression
                column = exp.to_column(node.name, dialect="postgres").name
                leaves.add("physical:" + ".".join(filter(None, (table.db, table.name, column))))
        dependencies.append((name, tuple(sorted(leaves))))
    # Reuse each already-qualified scope for all outputs. Predicates and joins can
    # depend on fields which are absent from the public value projections.
    scope_nodes = {id(scope): nodes}

    def leaves(root):
        result = set()
        for item in root.walk():
            if isinstance(item.expression, exp.Table):
                table = item.expression
                name = exp.to_column(item.name, dialect="postgres").name
                result.add("physical:" + ".".join(filter(None, (table.db, table.name, name))))
        return result

    kinds: dict[str, set[str]] = {}
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
            found = kinds.setdefault(kind, set())
            for column in clause.find_all(exp.Column):
                source = selected_scope.sources.get(column.table)
                if isinstance(source, exp.Table):
                    found.add(
                        "physical:" + ".".join(filter(None, (source.db, source.name, column.name)))
                    )
                elif source is not None:
                    if id(source) not in scope_nodes:
                        scope_nodes[id(source)] = lineage(
                            None, source.expression, schema=schema, scope=source, dialect="postgres"
                        )
                    source_nodes = scope_nodes[id(source)]
                    if isinstance(source_nodes, dict) and column.name in source_nodes:
                        found.update(leaves(source_nodes[column.name]))
                elif not column.table and column.name in nodes:
                    found.update(leaves(nodes[column.name]))
    relational_dependencies = tuple(
        (kind, tuple(sorted(fields))) for kind, fields in sorted(kinds.items())
    )
    types = tuple(
        (value.alias_or_name, value.type.sql(dialect="postgres") if value.type else "UNKNOWN")
        for value in qualified.selects
    )
    unknowns = [f"unknown output type: {name}" for name, typ in types if typ == "UNKNOWN"]
    for node in qualified.walk():
        if isinstance(node, exp.DataType) and any(
            _incomplete_type(value)
            for value in node.walk()
            if isinstance(value, exp.DataType)
        ):
            unknowns.append("incomplete declared type: " + node.sql(dialect="postgres"))
    for field in recipe.fields:
        if not field.source:
            unknowns.append("missing output model origin: " + field.name)
    for value in qualified.selects:
        if value.this.meta.get("model_source") != expected_origins[value.alias_or_name]:
            unknowns.append("transformed output model origin unavailable: " + value.alias_or_name)
    unknowns.extend(
        "helper body not analyzed: " + helper.function_name for helper in recipe.helpers
    )
    return ProjectionAnalysis(
        recipe.projection_id,
        "companion-query-analysis-2",
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
                    if table.db + "." + table.name in metadata.tables
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
    )
