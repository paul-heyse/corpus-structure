"""Restore PostgreSQL column-index collations omitted by SQLAlchemy 2.1.6.

The pinned dialect reflects a simple indexed column by name and omits its
``pg_index.indcollation`` override. Alembic otherwise proposes rebuilding the
same collated index forever. Enrich this authoring context's reflected records
from the actual catalog before normal index comparison; never copy the target
collation or discard a difference. Remove when the pinned dialect reflects it.
"""

from __future__ import annotations

from typing import Any

from alembic.autogenerate.compare.util import _InspectorConv
from alembic.runtime.plugins import Plugin
from alembic.util import DispatchPriority, PriorityDispatchResult
from sqlalchemy import text


def restore_column_index_collations(
    context: Any,
    operations: Any,
    schema: Any,
    name: Any,
    inspected: Any,
    declared: Any,
) -> PriorityDispatchResult:
    if inspected is None or declared is None:
        return PriorityDispatchResult.CONTINUE
    # _InspectorConv is pinned Alembic's shared reflection-cache owner. Both this
    # hook and its ordinary index comparator consume the same per-context records.
    indexes = {
        str(index["name"]): index
        for index in _InspectorConv(context.inspector).get_indexes(name, schema=schema)
    }
    rows = context.connection.execute(
        text("""
        SELECT idx.relname AS index_name, key.ordinality - 1 AS position,
               attribute.attname AS column_name, namespace.nspname AS collation_schema,
               coll.collname AS collation_name
        FROM pg_catalog.pg_index definition
        JOIN pg_catalog.pg_class relation ON relation.oid=definition.indrelid
        JOIN pg_catalog.pg_namespace relation_namespace
            ON relation_namespace.oid=relation.relnamespace
        JOIN pg_catalog.pg_class idx ON idx.oid=definition.indexrelid
        CROSS JOIN LATERAL unnest(definition.indkey::smallint[], definition.indcollation::oid[])
            WITH ORDINALITY AS key(attribute_number, collation_id, ordinality)
        JOIN pg_catalog.pg_attribute attribute ON attribute.attrelid=relation.oid
            AND attribute.attnum=key.attribute_number
        JOIN pg_catalog.pg_collation coll ON coll.oid=key.collation_id
        JOIN pg_catalog.pg_namespace namespace ON namespace.oid=coll.collnamespace
        WHERE relation_namespace.nspname=:schema AND relation.relname=:name
          AND key.ordinality<=definition.indnkeyatts
          AND key.collation_id<>attribute.attcollation
    """),
        {"schema": schema or context.connection.dialect.default_schema_name, "name": name},
    ).mappings()
    quote = context.connection.dialect.identifier_preparer.quote
    for row in rows:
        index = indexes.get(row["index_name"])
        if index is None:
            continue
        position, column = row["position"], row["column_name"]
        if index["column_names"][position] != column:
            raise RuntimeError("reflected index column differs from PostgreSQL catalog")
        collation = quote(row["collation_name"])
        if row["collation_schema"] != "pg_catalog":
            collation = quote(row["collation_schema"]) + "." + collation
        expression = quote(column) + " COLLATE " + collation
        if "expressions" not in index:
            if any(value is None for value in index["column_names"]):
                raise RuntimeError("reflected expression index has no expressions")
            index["expressions"] = [value for value in index["column_names"] if value is not None]
        expressions = index["expressions"]
        expressions[position] = expression
        index["column_names"][position] = None
        sorting = index.get("column_sorting", {})
        if column in sorting:
            sorting[expression] = sorting.pop(column)
    return PriorityDispatchResult.CONTINUE


plugin = Plugin("corpus.semantic.index_collations")
plugin.add_autogenerate_comparator(
    restore_column_index_collations,
    "table",
    "indexes",
    qualifier="postgresql",
    priority=DispatchPriority.FIRST,
)
