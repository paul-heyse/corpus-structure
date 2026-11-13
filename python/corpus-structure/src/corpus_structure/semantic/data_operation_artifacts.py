"""Pure derived call products: one model and its trusted physical correspondences.

This is an archive product, never a second editable call declaration or permission.
Preparation does not import any operation implementation.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, replace
from hashlib import sha256
from pathlib import Path

from .contracts import OperationCallBinding, OperationFieldBinding
from .data_operation_identity import ENCODING_VERSION
from .data_operation_model import EffectiveDataOperationModel, EffectiveOperation, OperationRole
from .identity import canonical_bytes
from .operation_call_generation import render_call_bindings, render_call_identifiers
from .types import SourceArtifact

GENERATOR_VERSION = "data-operation-ports-v1"
_GENERATOR_FILES = ("data_operation_artifacts.py", "operation_call_generation.py", "data_operation_ports.py")


def capture_port_generator_sources() -> tuple[SourceArtifact, ...]:
    """Acquire installed generator/runtime sources once, at explicit acquisition."""
    return tuple(
        SourceArtifact("generator/" + name, Path(__file__).with_name(name).read_bytes())
        for name in _GENERATOR_FILES
    )



@dataclass(frozen=True)
class DataOperationArtifacts:
    manifest: bytes
    calls: bytes
    identifiers: bytes

    @property
    def files(self) -> tuple[tuple[str, bytes], ...]:
        return (
            ("data_operation_ports.json", self.manifest),
            ("data_operation_calls.py", self.calls),
            ("data_operation_ids.py", self.identifiers),
        )


def compile_data_operation_artifacts(
    model: EffectiveDataOperationModel,
    native_calls: tuple[tuple[str, OperationCallBinding], ...],
    *,
    native_source_digest: str,
    generator_sources: tuple[SourceArtifact, ...] | None = None,
) -> DataOperationArtifacts:
    """Derive immutable products using the same native/nominal/Pydantic emitter.

    `native_calls` is acquired from the trusted physical-model owner. Its source
    digest and complete resolved field representation are release determinants.
    The caller archives these products and native admission authenticates them;
    producing this object does not admit a model or authorize SQL execution.
    """
    # Normal release preparation supplies the archived acquisition explicitly.
    # Standalone callers can deliberately acquire the current implementation.
    captured = capture_port_generator_sources() if generator_sources is None else generator_sources
    acquired = {source.name: source.content for source in captured}
    if len(acquired) != len(captured) or set(acquired) != {"generator/" + name for name in _GENERATOR_FILES}:
        raise ValueError("generator source acquisition is incomplete or repeated")
    current = {source.name: source.content for source in capture_port_generator_sources()}
    if acquired != current:
        raise ValueError("installed generator differs from captured preparation dependencies")
    if not native_source_digest:
        raise ValueError("trusted native correspondence source identity is required")
    calls = tuple((owner, replace(call, requires_context=True)) for owner, call in native_calls)
    names = [call.id for _, call in calls]
    if len(names) != len(set(names)):
        raise ValueError("native correspondence variant names must be unique")
    for owner, call in calls:
        operation = model.operation(owner)
        if not any(i.owner == owner and i.domain == "recipe" for i in model.identities):
            raise ValueError("native correspondence requires a complete effective recipe")
        _validate_native_correspondence(model, operation, call)
        if call.source_digest != native_source_digest:
            raise ValueError("native correspondence source identity differs from captured source")
    records = tuple((owner, asdict(call)) for owner, call in calls)
    correspondence = sha256(canonical_bytes(records)).hexdigest()
    source = render_call_bindings(
        calls,
        identifiers_module=".data_operation_ids",
        context_validator=(".data_operation_admission", "require_data_operation_call_context"),
        value_base=(".data_operation_ports", "DataOperationWireValue"),
        row_base=(".data_operation_ports", "DataOperationNativeRow"),
    ).encode()
    identifiers = render_call_identifiers(calls).encode()
    manifest = canonical_bytes(
        {
            "version": GENERATOR_VERSION,
            "model_digest": sha256(model.content).hexdigest(),
            "encoding": ENCODING_VERSION,
            "binding_digest": sha256(canonical_bytes(json.loads(model.content)["bindings"])).hexdigest(),
            "native_source_digest": native_source_digest,
            "correspondence_digest": correspondence,
            "generator_digest": sha256(canonical_bytes(tuple((name, sha256(content).hexdigest()) for name, content in sorted(acquired.items())))).hexdigest(),
            "renderer_digest": sha256(acquired["generator/operation_call_generation.py"]).hexdigest(),
            "runtime_ports_digest": sha256(acquired["generator/data_operation_ports.py"]).hexdigest(),
            "calls_digest": sha256(source).hexdigest(),
            "identifiers_digest": sha256(identifiers).hexdigest(),
            "calls": records,
        }
    )
    return DataOperationArtifacts(manifest, source, identifiers)


# This finite lowering is deliberately narrower than the model's kind system.
# An object/enum/nullable/collection correspondence needs its own faithful typed
# lowering; assigning JSON or a familiar Python alias is not such a lowering.
_NATIVE_PRIMITIVES = {
    "string": "string", "integer": "integer", "boolean": "boolean",
    "float": "float", "double": "float", "decimal": "decimal",
    "datetime": "timestamp", "bytes": "bytes", "json": "json_payload",
}


def _validate_native_correspondence(
    model: EffectiveDataOperationModel, operation: EffectiveOperation, call: OperationCallBinding
) -> None:
    if call.backend != "native":
        raise ValueError("native artifact needs an explicitly admitted physical backend lowering")
    if not call.source_digest or any(
        field.resolved is None
        for field in (*call.parameters, *call.result_fields, *(f for r in call.records for f in r.fields))
    ):
        raise ValueError("native correspondence must have closed resolved source fields")
    for direction, fields in (("input", call.parameters), ("output", call.result_fields)):
        roles = tuple(r for r in operation.roles if r.direction == direction)
        if len({r.parameter or r.name for r in roles}) != len(roles) or {r.parameter or r.name for r in roles} != {f.name for f in fields} or len({f.name for f in fields}) != len(fields):
            raise ValueError("native fields differ from effective operation role correspondence")
        by_name = {field.name: field for field in fields}
        for role in roles:
            _validate_native_role(model, role, by_name[role.parameter or role.name])
    outputs = tuple(r for r in operation.roles if r.direction == "output")
    if call.ordered or call.order_by:
        raise ValueError("scalar native completion cannot invent collection order")
    if call.records:
        raise ValueError("nested native records require an explicit typed kind lowering")
    if outputs:
        if call.cardinality != "one" or call.result_mode not in {"scalar", "json", "table"}:
            raise ValueError("native completion cardinality differs from required scalar output roles")
        if call.result_mode == "scalar" and len(outputs) != 1:
            raise ValueError("native scalar completion requires exactly one output role")
        if call.result_mode in {"json", "table"} and not call.result_class:
            raise ValueError("native structured completion requires a typed result class")
        if call.result_mode == "json" and any(field.resolved is None or field.resolved.kind != "json_payload" for field in call.result_fields):
            raise ValueError("native JSON object fields need an explicit typed JSON lowering")
    elif call.cardinality != "none" or call.result_mode != "void":
        raise ValueError("native completion invents an undeclared result")


def _validate_native_role(
    model: EffectiveDataOperationModel, role: OperationRole, field: OperationFieldBinding
) -> None:
    kind = next(k for k in model.kinds if k.semantic_id == role.kind)
    facts = json.loads(kind.facts)
    primitive = facts.get("primitive") if kind.category == "primitive" else None
    native = _NATIVE_PRIMITIVES.get(primitive) if isinstance(primitive, str) else None
    resolved = field.resolved
    if native is None or resolved is None or resolved.kind != native:
        raise ValueError("native field type differs from effective semantic kind; explicit typed lowering required")
    if field.native_type is not None and native != "integer":
        raise ValueError("native SQL representation differs from semantic primitive")
    if field.semantic_type is not None or resolved.model_class is not None or resolved.enum_values or field.transform not in (None, "identity"):
        raise ValueError("native nominal/enum/transformed field requires an explicit typed kind lowering")
    if role.collection != "scalar" or role.minimum != 1 or role.maximum != 1 or role.presence != "required":
        raise ValueError("native nullable/optional/collection cardinality requires an explicit typed lowering")
    if field.nullable or resolved.nullable or field.multivalued or resolved.multivalued:
        raise ValueError("native nullability or collection differs from required scalar role")
    if field.default_json is not None:
        raise ValueError("native default requires a declared semantic parameter/default correspondence")
