"""Compare same-name CHECK predicates through PostgreSQL's actual bound expressions.

Alembic 1.20.1's by-name extension handles additions/removals, while its default
same-name comparison reports equality. Bind desired predicates on temporary
columns with the declared types before comparing catalog-normalized expressions.
"""

from __future__ import annotations

from typing import Any

from alembic.operations import ops
from alembic.runtime.plugins import Plugin
from alembic.util import DispatchPriority, PriorityDispatchResult
from sqlalchemy import CheckConstraint, Column, MetaData, Table, column, func, select
from sqlalchemy import table as sql_table
from sqlalchemy.schema import CreateTable, DropTable

from corpus_structure.schema.relational import physical_expression_sql


def _bound_checks(connection, relation):
    catalog = sql_table(
        "pg_constraint", column("conname"), column("conbin"), column("conrelid"),
        column("contype"), schema="pg_catalog",
    )
    return dict(connection.execute(select(
        catalog.c.conname, func.pg_catalog.pg_get_expr(catalog.c.conbin, catalog.c.conrelid)
    ).where(catalog.c.conrelid == func.pg_catalog.to_regclass(relation),
            catalog.c.contype == "c")).all())


def compare_existing_checks(
    context: Any, operations: Any, schema: Any, name: Any, inspected: Any, declared: Any,
) -> PriorityDispatchResult:
    if inspected is None or declared is None:
        return PriorityDispatchResult.CONTINUE
    constraints = {str(item.name): item for item in declared.constraints
                   if isinstance(item, CheckConstraint) and item.name is not None}
    if not constraints:
        return PriorityDispatchResult.CONTINUE
    quote = context.connection.dialect.identifier_preparer
    existing = _bound_checks(context.connection, quote.format_table(inspected))
    common = constraints.keys() & existing.keys()
    if not common:
        return PriorityDispatchResult.CONTINUE
    scratch = Table(
        "semantic_candidate_predicates", MetaData(),
        *(Column(item.name, item.type) for item in declared.columns),
        *(CheckConstraint(physical_expression_sql(constraints[key].sqltext), name=key)
          for key in sorted(common)),
        prefixes=["TEMPORARY"], postgresql_on_commit="DROP",
    )
    context.connection.execute(CreateTable(scratch))
    try:
        desired = _bound_checks(context.connection, "pg_temp.semantic_candidate_predicates")
    finally:
        context.connection.execute(DropTable(scratch))
    for key in sorted(common):
        if desired[key] == existing[key]:
            continue
        constraint = constraints[key]
        if context.run_object_filters(constraint, constraint.name, "check_constraint", False, None):
            previous = CheckConstraint(existing[key], name=key, table=inspected)
            operations.ops.append(ops.DropConstraintOp.from_constraint(previous))
            operations.ops.append(ops.CreateCheckConstraintOp.from_constraint(constraint))
    return PriorityDispatchResult.CONTINUE


plugin = Plugin("corpus.semantic.check_expressions")
plugin.add_autogenerate_comparator(
    compare_existing_checks, "table", "checkconstraints", qualifier="postgresql",
    priority=DispatchPriority.FIRST,
)
