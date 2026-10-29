"""Pinned Alembic 1.20 identity/default comparison integration.

Its callable-default path reads Identity.arg before dispatching identity comparison. Route
identity columns to the existing dialect comparer first; all other defaults retain normal
comparison. Remove this adapter when a pinned Alembic release fixes that ordering.
"""

from __future__ import annotations

from typing import Any

from alembic.autogenerate.compare.server_defaults import _compare_identity_default
from alembic.runtime.plugins import Plugin
from alembic.util import DispatchPriority, PriorityDispatchResult


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


plugin = Plugin("corpus.semantic.defaults")
plugin.add_autogenerate_comparator(
    compare_identity,
    "column",
    "server_default",
    qualifier="postgresql",
    priority=DispatchPriority.FIRST,
)
