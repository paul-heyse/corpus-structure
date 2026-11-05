"""Pinned Alembic 1.20.1 identity/default comparison integration.

Its callable-default path reads Identity.arg before dispatching identity comparison. Route
identity columns to the existing dialect comparer first; all other defaults retain normal
comparison. Remove this adapter when a pinned Alembic release fixes that ordering.
"""

from __future__ import annotations

from typing import Any

from alembic.autogenerate.compare.server_defaults import _compare_identity_default
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


def compare_identity(
    autogen_context: Any,
    alter_column_op: Any,
    schema: Any,
    tname: Any,
    cname: Any,
    inspected: Any,
    declared: Any,
) -> PriorityDispatchResult:
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
    """Avoid evaluating one volatile UUID default to compare it with itself.

    Other defaults retain Alembic's normal comparison, including changed expressions.
    """
    if (
        inspected.table.schema != "ops"
        or inspected.table.name != "task"
        or inspected.name != "invocation_key"
    ):
        return None

    def normalized(value: str | None) -> str:
        return (
            "".join((value or "").split())
            .replace("'legacy-task:'::text", "'legacy-task:'")
            .replace("(", "")
            .replace(")", "")
        )

    expected = "gen_random_uuid::text"
    if normalized(inspected_default) == normalized(rendered_default) == expected:
        return False
    return None


plugin = Plugin("corpus.semantic.defaults")
plugin.add_autogenerate_comparator(
    compare_identity,
    "column",
    "server_default",
    qualifier="postgresql",
    priority=DispatchPriority.FIRST,
)
