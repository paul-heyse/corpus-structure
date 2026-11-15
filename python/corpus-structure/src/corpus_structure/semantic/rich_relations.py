"""Invocation-owned typed relations for current rich property/occurrence kernels."""

from __future__ import annotations

from collections.abc import Callable, Sequence
from contextlib import closing
from tempfile import TemporaryDirectory

import duckdb
import pyarrow as pa

from .analytical_kernels import (
    DISAGREEMENTS_SQL,
    FUSE_SQL,
    VIEW_ALTERNATIVES,
    VIEW_CLAIMS,
    VIEW_ENTITIES,
    VIEW_IDENTITY,
    VIEWS_INPUTS,
    VIEWS_MACRO_NAME,
    VIEWS_MACRO_SQL,
    ViewSpec,
    operation_view_tables,
)

RICH_MEANINGS = pa.schema(
    [pa.field("key", pa.string(), nullable=False), pa.field("meaning", pa.string())]
)
RICH_FUSION_INPUT = pa.schema(
    [
        pa.field("fact_id", pa.string(), nullable=False),
        pa.field("occurrence_id", pa.string()),
        pa.field(
            "evidence", pa.list_(pa.field("item", pa.string(), nullable=False)), nullable=False
        ),
    ]
)


class RichRelationKernel:
    """Materialize each bounded result before unregistering its typed inputs.

    One real analytical connection belongs to this invocation. No relation or reader
    escapes its lifetime, and no old packet/spine is synthesized to acquire it.
    """

    def __init__(
        self,
        *,
        property_ids: frozenset[str],
        threads: int,
        memory_limit: str,
        check_active: Callable[[], None],
    ):
        if threads < 1 or not memory_limit:
            raise ValueError("rich analytical resources require an actual bounded profile")
        self.property_ids = property_ids
        self.threads, self.memory_limit, self.check_active = threads, memory_limit, check_active
        self._stack = None
        self._connection = None

    def __enter__(self):
        from contextlib import ExitStack

        if self._stack is not None:
            raise RuntimeError("rich analytical invocation is already open")
        self.check_active()
        stack = ExitStack()
        try:
            spill = stack.enter_context(TemporaryDirectory(prefix="corpus-rich-"))
            connection = stack.enter_context(
                closing(
                    duckdb.connect(
                        config={
                            "threads": self.threads,
                            "memory_limit": self.memory_limit,
                            "temp_directory": spill,
                        }
                    )
                )
            )
            connection.execute(VIEWS_MACRO_SQL)
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

    def _query(self, inputs, sql):
        self.check_active()
        connection = self._connection
        if connection is None:
            raise RuntimeError("rich analytical invocation is closed")
        registered = []
        try:
            for name, value in inputs.items():
                connection.register(name, value)
                registered.append(name)
            result = connection.sql(sql).to_arrow_table()
            self.check_active()
            return result
        finally:
            for name in reversed(registered):
                connection.unregister(name)

    def disagreements(self, meanings: pa.Table) -> pa.Table:
        return self._query({"meanings": self._checked(meanings, RICH_MEANINGS)}, DISAGREEMENTS_SQL)

    def fuse(self, candidates: pa.Table) -> pa.Table:
        return self._query(
            {"candidate_input": self._checked(candidates, RICH_FUSION_INPUT)}, FUSE_SQL
        )

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
        inputs = dict(
            zip(
                VIEWS_INPUTS,
                (
                    self._checked(claims, VIEW_CLAIMS),
                    self._checked(entities, VIEW_ENTITIES),
                    self._checked(identity, VIEW_IDENTITY),
                    self._checked(alternatives, VIEW_ALTERNATIVES),
                    spec_rows,
                    applies,
                ),
                strict=True,
            )
        )
        arguments = ",".join("'" + name + "'" for name in VIEWS_INPUTS)
        return self._query(inputs, f"SELECT * FROM {VIEWS_MACRO_NAME}({arguments})")
