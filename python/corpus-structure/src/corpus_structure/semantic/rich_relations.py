"""Invocation-owned typed relations for current rich property/occurrence kernels."""

from __future__ import annotations

from collections.abc import Callable, Sequence

import pyarrow as pa

from corpus_structure.analytics import connection as analytical_connection

from .analytical_kernels import (
    VIEW_ALTERNATIVES,
    VIEW_CLAIMS,
    VIEW_ENTITIES,
    VIEW_FACTS,
    VIEW_IDENTITY,
    ViewSpec,
    operation_view_tables,
    operation_views,
)


class RichRelationKernel:
    """Materialize each bounded result before releasing its typed input relations.

    One real analytical connection belongs to this invocation. No relation or reader
    escapes its lifetime, and no old packet/spine is synthesized to acquire it.
    """

    def __init__(
        self,
        *,
        property_ids: frozenset[str],
        check_active: Callable[[], None],
        observe_inputs: Callable[[dict[str, int]], None] | None = None,
    ):
        self.property_ids = property_ids
        self.check_active = check_active
        self.observe_inputs = observe_inputs
        self._stack = None
        self._connection = None

    def __enter__(self):
        from contextlib import ExitStack

        if self._stack is not None:
            raise RuntimeError("rich analytical invocation is already open")
        self.check_active()
        stack = ExitStack()
        try:
            connection = stack.enter_context(analytical_connection())
            self._stack, self._connection = stack, connection
            return self
        except BaseException:
            stack.close()
            raise

    def __exit__(self, *exception):
        stack, self._stack, self._connection = self._stack, None, None
        if stack is not None:
            return stack.__exit__(*exception)

    @staticmethod
    def _checked(table: pa.Table, schema: pa.Schema):
        if not isinstance(table, pa.Table) or not table.schema.remove_metadata().equals(
            schema.remove_metadata()
        ):
            raise ValueError("rich analytical relation differs from its actual typed schema")
        for field, column in zip(schema, table.columns, strict=True):
            if not field.nullable and column.null_count:
                raise ValueError("rich analytical relation has null in a required column")
        return table

    def _query(self, inputs, build):
        self.check_active()
        connection = self._connection
        if connection is None:
            raise RuntimeError("rich analytical invocation is closed")
        relations = [connection.from_arrow(table) for table in inputs]
        result = build(*relations).to_arrow_table().cast(VIEW_FACTS, safe=True)
        self.check_active()
        return result

    def views(
        self,
        *,
        claims: pa.Table,
        entities: pa.Table,
        identity: pa.Table,
        alternatives: pa.Table,
        specs: Sequence[ViewSpec],
    ) -> pa.Table:
        spec_rows, applies = operation_view_tables(specs, self.property_ids)
        inputs = (
            self._checked(claims, VIEW_CLAIMS),
            self._checked(entities, VIEW_ENTITIES),
            self._checked(identity, VIEW_IDENTITY),
            self._checked(alternatives, VIEW_ALTERNATIVES),
            spec_rows,
            applies,
        )
        if self.observe_inputs is not None:
            self.observe_inputs(
                dict(
                    zip(
                        ("claims", "entities", "identity", "alternatives", "specs", "applies"),
                        (table.num_rows for table in inputs),
                        strict=True,
                    )
                )
            )
        return self._query(inputs, operation_views)
