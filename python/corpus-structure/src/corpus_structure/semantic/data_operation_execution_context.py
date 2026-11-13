"""Acquire a native execution context from retained release/runtime inputs.

This opens no algorithm module, discovers no plugin and invents no runtime pin.
The execution owner separately acquires the actual callable and resources.
"""

from __future__ import annotations

import json
from dataclasses import dataclass

from sqlalchemy import Connection, select

from .composed import read_data_operation_inputs
from .metadata import table
from .python_operation_sources import PythonSourceCollection
from .refusals import SemanticRefusal
from .releases import load_release
from .runtime_binding_store import runtime_binding_for_release
from .runtime_bindings import RuntimeBinding
from .types import PreparedRelease, ResolvedDependencies, SourceArtifact, SourceBundle


@dataclass(frozen=True)
class DataOperationExecutionContext:
    prepared: PreparedRelease
    runtime: RuntimeBinding
    schema: SourceBundle
    sources: PythonSourceCollection


def load_data_operation_execution_context(
    connection: Connection,
    *,
    release: str,
    runtime: str,
) -> DataOperationExecutionContext:
    """Reverify archived meaning once at the execution boundary."""
    prepared = load_release(connection, release)
    binding = runtime_binding_for_release(connection, prepared, runtime)
    manifest = json.loads(prepared.manifest)
    inputs = table("sem.input")
    schema = SourceBundle(
        manifest["root"],
        tuple(
            SourceArtifact(row.input_name, bytes(row.content))
            for row in connection.execute(
                select(inputs.c.input_name, inputs.c.content)
                .where(
                    inputs.c.release_id == release,
                    inputs.c.input_kind == "source",
                )
                .order_by(inputs.c.input_name)
            )
        ),
    )
    if sorted((item.name, item.digest) for item in schema.sources) != [
        tuple(item) for item in manifest["sources"]
    ]:
        raise SemanticRefusal("retained execution schemas differ from the release manifest")
    captured = read_data_operation_inputs(
        ResolvedDependencies(
            tuple(
                SourceArtifact(item.kind, item.content)
                for item in prepared.artifacts
                if item.kind.startswith("data-operations/")
            )
        )
    )
    if captured is None or captured[1] is None:
        raise SemanticRefusal("release lacks captured Python execution inputs")
    return DataOperationExecutionContext(prepared, binding, schema, captured[1])
