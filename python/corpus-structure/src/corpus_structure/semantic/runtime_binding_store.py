"""Native custody of immutable runtime provenance and same-release run pins."""

from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import Connection, select

from .metadata import table
from .runtime_bindings import RuntimeBinding, validate_runtime_binding
from .types import PreparedRelease, SourceArtifact

if TYPE_CHECKING:
    from ._operation_ids import RuntimeId


def persist_runtime_binding(
    conn: Connection, prepared: PreparedRelease, binding: RuntimeBinding
) -> RuntimeId:
    """Validate exact bytes before the operation-owned, idempotent native registration."""
    from ._operation_calls import ReleaseId, RuntimeId, register_runtime_binding

    validate_runtime_binding(binding, prepared)
    return register_runtime_binding(
        conn,
        release_id=ReleaseId(binding.release_id),
        runtime_id=RuntimeId(binding.runtime_id),
        manifest=binding.manifest,
        archive=binding.archive,
        projection_context=prepared,
    )


def runtime_binding_for_run(
    conn: Connection, run_id: int, prepared: PreparedRelease
) -> RuntimeBinding:
    """Read the selected immutable provenance; never synthesize a pin from current code."""
    run = table("ops.run")
    selected = conn.execute(
        select(run.c.release_id, run.c.runtime_id).where(run.c.id == run_id)
    ).one()
    if selected.release_id != prepared.release_id:
        raise ValueError("run and prepared release differ")
    if selected.runtime_id is None:
        from .runtime_bindings import legacy_runtime_binding

        archived_input = table("sem.input")
        prefix = "execution/implementation/"
        inputs = tuple(
            SourceArtifact(row.input_name.removeprefix(prefix), bytes(row.content))
            for row in conn.execute(
                select(archived_input.c.input_name, archived_input.c.content).where(
                    archived_input.c.release_id == prepared.release_id,
                    archived_input.c.input_kind == "dependency",
                    archived_input.c.input_name.startswith(prefix),
                ).order_by(archived_input.c.input_name)
            )
        )
        return legacy_runtime_binding(prepared, inputs)
    stored = table("sem.runtime_binding")
    row = conn.execute(
        select(stored).where(
            stored.c.release_id == selected.release_id,
            stored.c.runtime_id == selected.runtime_id,
        )
    ).mappings().one()
    binding = RuntimeBinding(
        row["release_id"],
        row["runtime_id"],
        bytes(row["manifest_bytes"]),
        bytes(row["archive_bytes"]),
    )
    validate_runtime_binding(binding, prepared)
    return binding
