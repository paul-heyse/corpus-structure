"""Target model correspondence and acquired native admission boundaries."""

from __future__ import annotations

import json
from dataclasses import dataclass
from hashlib import sha256
from typing import TYPE_CHECKING

from .data_operation_model import MODEL_VERSION, read_effective_data_operations
from .data_operation_ports import PythonPortIdentity
from .identity import canonical_bytes
from .refusals import SemanticRefusal


def _source_identity_bytes(identity: PythonPortIdentity) -> bytes:
    from dataclasses import asdict

    record = asdict(identity)
    record["capabilities"] = json.loads(identity.capabilities)
    return canonical_bytes(record)


if TYPE_CHECKING:
    from sqlalchemy import Connection

    from .data_operation_model import EffectiveDataOperationModel
    from .python_operation_sources import PythonSourceCollection
    from .runtime_bindings import RuntimeBinding
    from .types import PreparedRelease, SourceArtifact, SourceBundle


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
    model = read_effective_data_operations(artifacts[0].content)
    if model.version != MODEL_VERSION:
        raise SemanticRefusal("execution requires the current target operation model; regenerate")
    return model


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
    from .data_operation_storage import admit_data_operation_definitions

    model = bound_data_operation_model(prepared)
    return admit_data_operation_definitions(connection, prepared, model)


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
        if _source_identity_bytes(identity) != self.identity:
            raise SemanticRefusal("callable differs from acquired execution admission")


@dataclass(frozen=True)
class PreparedCapabilityIdentity(PythonPortIdentity):
    """Source correspondence plus exact prepared-resource runtime custody."""

    runtime: str
    assets: bytes


@dataclass(frozen=True)
class AcquiredPreparedExecution:
    identity: PreparedCapabilityIdentity
    source_admission: AcquiredPythonExecution
    custody: tuple[SourceArtifact, ...]

    def authorize(self, identity: PreparedCapabilityIdentity) -> None:
        if identity != self.identity:
            raise SemanticRefusal("prepared capability differs from acquired admission")


def acquire_prepared_execution(
    connection: Connection,
    prepared: PreparedRelease,
    sources: PythonSourceCollection,
    operation: str,
    runtime: RuntimeBinding,
    *,
    schema: SourceBundle | None = None,
) -> AcquiredPreparedExecution:
    """Acquire declared preparation, retaining source and opaque asset custody.

    The concrete capability still verifies its original callable, resources and
    supported preparation profile. This admission never interprets a profile name
    as permission to execute arbitrary callbacks.
    """
    from dataclasses import asdict

    model = bound_data_operation_model(prepared)
    selected = model.operation(operation)
    if selected.capabilities.preparation == "none":
        raise SemanticRefusal("prepared execution requires declared preparation")
    admission = acquire_python_execution(
        connection, prepared, sources, operation, runtime, schema=schema
    )
    archived = json.loads(runtime.archive)["inputs"]
    retained = {item["sha256"] for item in archived}
    boundaries = (
        *selected.assets,
        *(
            boundary
            for implementation in model.implementation_slices
            if implementation.root == selected.implementation_root
            for boundary in implementation.boundaries
        ),
    )
    if any(
        boundary.content_digest is None or boundary.content_digest not in retained
        for boundary in boundaries
    ):
        raise SemanticRefusal(
            "prepared asset or implementation boundary lacks exact runtime custody"
        )
    source_record = json.loads(admission.identity)
    source_record["capabilities"] = canonical_bytes(source_record["capabilities"])
    identity = PreparedCapabilityIdentity(
        **source_record,
        runtime=runtime.runtime_id,
        assets=canonical_bytes(tuple(asdict(boundary) for boundary in boundaries)),
    )
    return AcquiredPreparedExecution(identity, admission, sources.boundary_contracts)


def acquire_python_execution(
    connection: Connection,
    prepared: PreparedRelease,
    sources: PythonSourceCollection,
    operation: str,
    runtime: RuntimeBinding,
    *,
    schema: SourceBundle | None = None,
) -> AcquiredPythonExecution:
    """Acquire permissions briefly; no DB connection is retained through computation."""
    from sqlalchemy import select

    from .data_operation_ports import python_port_identity
    from .data_operation_storage import require_data_operation_native
    from .metadata import table
    from .runtime_bindings import validate_runtime_binding

    model = bound_data_operation_model(prepared)
    require_data_operation_native(connection, prepared)
    validate_runtime_binding(runtime, prepared)
    if schema is not None:
        manifest = json.loads(prepared.manifest)
        if schema.root != manifest["root"] or sorted(
            (item.name, item.digest) for item in schema.sources
        ) != [tuple(item) for item in manifest["sources"]]:
            raise SemanticRefusal("callable schema differs from captured release inputs")
    identity = python_port_identity(model, sources, operation, schema=schema, prepared=prepared)
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
    retained_contracts = {
        (item["name"], item["sha256"])
        for item in json.loads(runtime.manifest)["implementation_inputs"]
    }
    if any(
        ("data-operations/contracts/" + contract.name, contract.digest) not in retained_contracts
        for contract in sources.boundary_contracts
    ):
        raise SemanticRefusal("Python boundary contract differs from acquired runtime custody")
    return AcquiredPythonExecution(
        _source_identity_bytes(identity),
        prepared.release_id,
        runtime.runtime_id,
        json.loads(runtime.manifest)["attestation"],
    )


def acquire_publication_port(connection: Connection, prepared: PreparedRelease):
    """Acquire the fixed receipt-bearing native command, not Python effect callbacks."""
    from sqlalchemy import select

    from .data_operation_ports import ResolvedPublicationPort
    from .data_operation_storage import DataOperationStorage, require_data_operation_native
    from .metadata import table

    model = bound_data_operation_model(prepared)
    operation = model.operation("data.publish_data_derivation")
    if operation.profile != "command" or not operation.effects:
        raise SemanticRefusal("publication requires its captured effectful command contract")
    roles = {role.name: role for role in operation.roles}
    if set(roles) != {"request", "result"}:
        raise SemanticRefusal("publication command correspondence differs")
    contracts = {
        identity.owner: identity.key for identity in model.identities if identity.domain == "kind"
    }
    require_data_operation_native(connection, prepared)
    definitions = table("sem.data_operation_definition")
    admitted = (
        connection.execute(
            select(definitions).where(
                definitions.c.release_id == prepared.release_id,
                definitions.c.operation_id == operation.semantic_id,
            )
        )
        .mappings()
        .one()
    )
    identities = {(value.owner, value.domain): value.key for value in model.identities}
    if (
        admitted["profile"] != "command"
        or admitted["recipe"] != identities[operation.semantic_id, "recipe"]
        or {role["name"]: role["kind_contract"] for role in admitted["input_roles"]}
        != {"request": contracts[roles["request"].kind]}
        or {role["name"]: role["kind_contract"] for role in admitted["output_roles"]}
        != {"result": contracts[roles["result"].kind]}
    ):
        raise SemanticRefusal("publication command differs from native admitted release")
    return ResolvedPublicationPort(
        DataOperationStorage(connection),
        contracts[roles["request"].kind],
        contracts[roles["result"].kind],
    )
