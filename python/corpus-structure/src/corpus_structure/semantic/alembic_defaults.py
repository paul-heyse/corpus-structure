"""Pinned Alembic 1.20.1 generated/default comparison integration.

Its callable-default path reads `arg` before dispatching Identity and Computed comparison.
Route both to Alembic's specialized comparers first. Frozen native admission still verifies
exact generated expressions. Remove this adapter when the pinned release fixes that ordering.
"""

from __future__ import annotations

from typing import Any

from alembic.autogenerate.compare.server_defaults import (
    _compare_computed_default,
    _compare_identity_default,
)
from alembic.runtime.plugins import Plugin
from alembic.util import DispatchPriority, PriorityDispatchResult
from sqlalchemy import ARRAY


def compare_type(ctx, inspected_column, metadata_column, inspected_type, metadata_type):
    """Preserve array cardinality when Alembic tokenizes TEXT[] as plain TEXT.

    Delegate all remaining element and scalar comparisons to the dialect.
    """
    if isinstance(inspected_type, ARRAY) != isinstance(metadata_type, ARRAY):
        return True
    return None


def _bound_column(context, column):
    columns = context.opts.get("declared_physical_columns", {})
    return columns.get(column.table.fullname, {}).get(column.name)


def compare_generated_default(
    autogen_context: Any,
    alter_column_op: Any,
    schema: Any,
    tname: Any,
    cname: Any,
    inspected: Any,
    declared: Any,
) -> PriorityDispatchResult:
    if inspected.computed is not None or declared.computed is not None:
        bound = _bound_column(autogen_context.migration_context, declared)
        if (
            bound is not None
            and bound["generated"]
            and inspected.computed is not None
            and declared.computed is not None
            and str(inspected.computed.sqltext).strip() == bound["default"]
            and inspected.computed.persisted == declared.computed.persisted
        ):
            return PriorityDispatchResult.STOP
        return _compare_computed_default(
            autogen_context, alter_column_op, schema, tname, cname, inspected, declared
        )
    if inspected.identity is None and declared.identity is None:
        return PriorityDispatchResult.CONTINUE
    _compare_identity_default(
        autogen_context, alter_column_op, schema, tname, cname, inspected, declared
    )
    return PriorityDispatchResult.STOP


def compare_default(
    ctx: Any,
    inspected: Any,
    declared: Any,
    inspected_default: str | None,
    metadata_default: Any,
    rendered_default: str | None,
) -> bool | None:
    """Compare server-bound declarations without evaluating default expressions."""
    bound = _bound_column(ctx, declared)
    if bound is None:
        return None
    return inspected_default != bound["default"]


plugin = Plugin("corpus.semantic.defaults")
plugin.add_autogenerate_comparator(
    compare_generated_default,
    "column",
    "server_default",
    qualifier="postgresql",
    priority=DispatchPriority.FIRST,
)
