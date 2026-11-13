"""Target model correspondence and acquired native admission boundaries."""

from __future__ import annotations

import json
from dataclasses import dataclass
from hashlib import sha256
from typing import TYPE_CHECKING

from .data_operation_model import read_effective_data_operations
from .identity import canonical_bytes
from .refusals import SemanticRefusal

if TYPE_CHECKING:
    from sqlalchemy import Connection

    from .data_operation_model import EffectiveDataOperationModel
    from .data_operation_ports import PythonPortIdentity
    from .python_operation_sources import PythonSourceCollection
    from .runtime_bindings import RuntimeBinding
    from .types import PreparedRelease


def bound_data_operation_model(prepared: PreparedRelease) -> EffectiveDataOperationModel:
    """Read archived effective meaning; this grants no runtime or database permission."""
    artifacts = [a for a in prepared.artifacts if a.kind == "data_operations.json"]
    manifest = json.loads(prepared.manifest)
    if (
        prepared.execution_model_id is not None
        or len(artifacts) != 1
        or manifest.get("data_operation_model") != artifacts[0].digest
    ):
        raise SemanticRefusal("release lacks an unambiguous target operation model")
    return read_effective_data_operations(artifacts[0].content)


def require_data_operation_call_context(
    prepared: PreparedRelease, operation: str, variant: str, contract_digest: str
) -> None:
    """Check immutable correspondence, separately from actual acquired authorization."""
    model = bound_data_operation_model(prepared)
    artifacts = [a for a in prepared.artifacts if a.kind == "data_operation_ports.json"]
    if len(artifacts) != 1:
        raise SemanticRefusal("release lacks target call correspondence")
    manifest = json.loads(artifacts[0].content)
    if manifest["model_digest"] != sha256(model.content).hexdigest():
        raise SemanticRefusal("target correspondence belongs to another effective model")
    calls = [
        call for owner, call in manifest["calls"] if owner == operation and call["id"] == variant
    ]
    if len(calls) != 1 or sha256(canonical_bytes(calls)).hexdigest() != contract_digest:
        raise SemanticRefusal(f"{operation}/{variant}: incompatible target call correspondence")


def admit_data_operation_release(connection: Connection, prepared: PreparedRelease) -> str:
    """Require the actual trusted kernel, then admit exact compiled definitions."""
    from .data_operation_storage import (
        admit_data_operation_definitions,
        require_data_operation_native,
    )

    model = bound_data_operation_model(prepared)
    native = require_data_operation_native(connection, prepared)
    admit_data_operation_definitions(connection, prepared, model)
    return native


@dataclass(frozen=True)
class AcquiredPythonExecution:
    """Private computation capability acquired from an admitted native release/runtime.

    It grants no publication rights. Completion still needs its current native
    claim, support/trust checks and exact admitted receipt.
    """

    identity: bytes
    release: str
    runtime: str
    attestation: str

    def authorize(self, identity: PythonPortIdentity) -> None:
        from dataclasses import asdict

        if canonical_bytes(asdict(identity)) != self.identity:
            raise SemanticRefusal("callable differs from acquired execution admission")


def acquire_python_execution(
    connection: Connection,
    prepared: PreparedRelease,
    sources: PythonSourceCollection,
    operation: str,
    runtime: RuntimeBinding,
) -> AcquiredPythonExecution:
    """Acquire permissions briefly; no DB connection is retained through computation."""
    from dataclasses import asdict

    from sqlalchemy import select

    from .data_operation_ports import python_port_identity
    from .data_operation_storage import require_data_operation_native
    from .metadata import table
    from .runtime_bindings import validate_runtime_binding

    model = bound_data_operation_model(prepared)
    require_data_operation_native(connection, prepared)
    validate_runtime_binding(runtime, prepared)
    identity = python_port_identity(model, sources, operation)
    definition = table("sem.data_operation_definition")
    row = (
        connection.execute(
            select(definition).where(
                definition.c.release_id == prepared.release_id,
                definition.c.operation_id == operation,
            )
        )
        .mappings()
        .one()
    )
    if (
        row["recipe"] != identity.recipe
        or row["implementation_revision"] != identity.implementation
    ):
        raise SemanticRefusal("Python implementation differs from native admitted recipe")
    stored = table("sem.runtime_binding")
    custody = (
        connection.execute(
            select(stored).where(
                stored.c.release_id == prepared.release_id,
                stored.c.runtime_id == runtime.runtime_id,
            )
        )
        .mappings()
        .one()
    )
    if (
        bytes(custody["manifest_bytes"]) != runtime.manifest
        or bytes(custody["archive_bytes"]) != runtime.archive
    ):
        raise SemanticRefusal("Python runtime differs from native retained custody")
    # Every supplied module must be among the exact captured executable inputs.
    retained = {item["sha256"] for item in json.loads(runtime.manifest)["implementation_inputs"]}
    if any(sha256(source.content).hexdigest() not in retained for source in sources.sources):
        raise SemanticRefusal("Python module is absent from acquired runtime custody")
    return AcquiredPythonExecution(
        canonical_bytes(asdict(identity)),
        prepared.release_id,
        runtime.runtime_id,
        json.loads(runtime.manifest)["attestation"],
    )
