"""Native custody of immutable runtime provenance and same-release run pins."""

from __future__ import annotations

from sqlalchemy import Connection, select

from .data_operation_runtime import (
    RuntimeBinding,
    RuntimeBindingError,
    validate_data_operation_runtime,
)
from .identifiers import RuntimeId
from .types import PreparedRelease


def persist_runtime_binding(
    conn: Connection, prepared: PreparedRelease, binding: RuntimeBinding
) -> RuntimeId:
    """Validate exact bytes before the operation-owned, idempotent native registration."""
    from sqlalchemy import bindparam, func

    from .data_operation_runtime import validate_data_operation_runtime

    validate_data_operation_runtime(binding, prepared)
    acquired = conn.scalar(
        select(
            func.sem.register_runtime_binding(
                bindparam("release"),
                bindparam("runtime"),
                bindparam("manifest"),
                bindparam("archive"),
            )
        ),
        {
            "release": binding.release_id,
            "runtime": binding.runtime_id,
            "manifest": binding.manifest,
            "archive": binding.archive,
        },
    )
    if acquired != binding.runtime_id:
        raise RuntimeBindingError("native registration returned a different runtime identity")
    return RuntimeId(acquired)


def runtime_binding_for_release(
    conn: Connection,
    prepared: PreparedRelease,
    runtime_id: str,
) -> RuntimeBinding:
    """Acquire exact retained release/runtime custody without a legacy run anchor."""
    if not runtime_id:
        raise RuntimeBindingError("release has no explicit immutable runtime pin")
    from ._typed_columns import sem_runtime_binding

    stored = sem_runtime_binding
    row = (
        conn.execute(
            select(stored).where(
                stored.c.release_id == prepared.release_id,
                stored.c.runtime_id == runtime_id,
            )
        )
        .mappings()
        .one()
    )
    binding = RuntimeBinding(
        row["release_id"],
        row["runtime_id"],
        bytes(row["manifest_bytes"]),
        bytes(row["archive_bytes"]),
    )
    validate_data_operation_runtime(binding, prepared)
    return binding
