"""Immutable compiler products for declared data operations.

Source locations and fact origins are diagnostic evidence. Semantic payloads contain
stable references and effective meaning only, before any release identity exists.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from typing import Literal

from .identity import canonical_bytes

MODEL_VERSION = "data-operation-model-v1"


@dataclass(frozen=True)
class FactOrigin:
    field: str
    category: Literal["authored", "extracted", "inferred", "modeled"]
    source: str
    declaration: str
    exposed_as: str | None = None
    line: int | None = None


@dataclass(frozen=True)
class SemanticNode:
    id: str
    category: str
    payload: bytes

    def record(self) -> dict:
        return {"id": self.id, "category": self.category, "payload": json.loads(self.payload)}


@dataclass(frozen=True)
class SemanticEdge:
    source: str
    target: str
    relation: str
    role: str = ""
    position: int | None = None
    multiplicity: int = 1


@dataclass(frozen=True)
class EffectiveKind:
    semantic_id: str
    name: str
    category: Literal["class", "property", "type", "enum", "primitive"]
    facts: bytes
    origins: tuple[FactOrigin, ...] = ()
    complete: bool = True
    unknowns: tuple[SourceUnknown, ...] = ()


@dataclass(frozen=True)
class InputSupport:
    provenance: Literal["exact", "value_substitution"]
    source: str
    coverage: str
    authorization: tuple[str, ...] = ()
    closure: tuple[str, ...] = ()
    identity_requirements: tuple[Literal["episode", "provider", "alternative"], ...] = ()


@dataclass(frozen=True)
class OperationRole:
    name: str
    kind: str
    direction: Literal["input", "output"]
    minimum: int
    maximum: int | None
    collection: Literal["scalar", "sequence", "bag", "set"]
    presence: Literal["required", "optional", "alternative"]
    support: InputSupport | None = None
    parameter: str | None = None
    alternatives: tuple[str, ...] = ()
    selected: str | None = None


@dataclass(frozen=True)
class BindingField:
    role: str
    projection: str
    field: str


@dataclass(frozen=True)
class BindingExpression:
    """Closed relational vocabulary; never SQL text or an executable callback."""

    operator: Literal[
        "scan",
        "join",
        "equal",
        "literal",
        "same",
        "distinct",
        "cardinality",
        "collection",
        "all",
        "choice",
        "optional",
        "forall",
        "absent",
    ]
    roles: tuple[str, ...] = ()
    fields: tuple[BindingField, ...] = ()
    value: bytes | None = None
    children: tuple[BindingExpression, ...] = ()
    minimum: int | None = None
    maximum: int | None = None
    collection: Literal["scalar", "sequence", "bag", "set"] | None = None
    selected: str | None = None
    population: str | None = None
    impact: Literal["result", "eligibility"] = "result"


@dataclass(frozen=True)
class RelationalBinding:
    semantic_id: str
    operation: str
    expression: BindingExpression
    origins: tuple[FactOrigin, ...] = ()


@dataclass(frozen=True)
class CallableParameter:
    name: str
    kind: str
    annotation: str | None
    default: str | None


@dataclass(frozen=True)
class CallableSurface:
    exposed: str
    declaration: str
    parameters: tuple[CallableParameter, ...]
    returns: str | None
    overloads: tuple[bytes, ...] = ()


@dataclass(frozen=True)
class StateDimension:
    name: str
    values: tuple[str, ...]


@dataclass(frozen=True)
class StateTransition:
    dimension: str
    before: str
    after: str
    outcome: str
    effects: tuple[str, ...] = ()


@dataclass(frozen=True)
class EffectContract:
    name: str
    authorization: tuple[str, ...]
    idempotency: str
    fulfillment: str


@dataclass(frozen=True)
class ImplementationCapabilities:
    forms: tuple[Literal["scalar", "batch", "stream"], ...]
    preparation: str
    cancellation: str
    ownership: str
    limits: tuple[str, ...] = ()


@dataclass(frozen=True)
class OpaqueBoundary:
    reference: str
    contract: str
    role: str
    content_digest: str | None = None


@dataclass(frozen=True)
class SourceUnknown:
    source: str
    location: str
    reason: str
    required: bool = True


@dataclass(frozen=True)
class ImplementationSlice:
    root: str
    nodes: tuple[SemanticNode, ...]
    edges: tuple[SemanticEdge, ...]
    boundaries: tuple[OpaqueBoundary, ...] = ()
    unknowns: tuple[SourceUnknown, ...] = ()
    normalization: str = "python-cst-v1"

    @property
    def complete(self) -> bool:
        return not any(item.required for item in self.unknowns)

    def semantic_records(self) -> dict:
        return {
            "nodes": tuple(node.record() for node in self.nodes),
            "edges": tuple(asdict(edge) for edge in self.edges),
            "boundaries": tuple(asdict(boundary) for boundary in self.boundaries),
            "unknowns": tuple(asdict(unknown) for unknown in self.unknowns),
            "normalization": self.normalization,
        }


@dataclass(frozen=True)
class EffectiveIdentity:
    owner: str
    domain: str
    key: str
    canonical_input: bytes


@dataclass(frozen=True)
class EffectiveOperation:
    semantic_id: str
    profile: Literal["derivation", "discovery", "selection", "command", "read"]
    subject: str
    context: tuple[str, ...]
    roles: tuple[OperationRole, ...]
    applicability: tuple[str, ...]
    invariants: tuple[str, ...]
    coverage: str
    outcomes: tuple[str, ...]
    precision: str
    dependencies: tuple[str, ...]
    state_dimensions: tuple[StateDimension, ...]
    transitions: tuple[StateTransition, ...]
    effects: tuple[EffectContract, ...]
    capabilities: ImplementationCapabilities
    behavior: str
    parameters: bytes
    assets: tuple[OpaqueBoundary, ...]
    callable_surfaces: tuple[CallableSurface, ...]
    implementation_root: str | None
    origins: tuple[FactOrigin, ...]
    binding: str
    replicate_policy: str = "deterministic-single-result"
    support_policy: str = "all-declared-input-support"

    @property
    def recipe(self) -> bytes:
        """Eligibility-only rules have a separate identity; support/scope remain determinants."""
        return canonical_bytes(
            {
                "id": self.semantic_id,
                "profile": self.profile,
                "subject": self.subject,
                "context": self.context,
                "roles": [asdict(role) for role in self.roles],
                "invariants": self.invariants,
                "coverage": self.coverage,
                "outcomes": self.outcomes,
                "precision": self.precision,
                "dependencies": self.dependencies,
                "behavior": self.behavior,
                "parameters": json.loads(self.parameters),
                "assets": [asdict(a) for a in self.assets],
                "effects": [asdict(effect) for effect in self.effects],
                "replicate_policy": self.replicate_policy,
                "support_policy": self.support_policy,
            }
        )

    @property
    def eligibility(self) -> bytes:
        return canonical_bytes(
            {
                "operation": self.semantic_id,
                "applicability": self.applicability,
                "binding": self.binding,
            }
        )

    @property
    def definition(self) -> bytes:
        return canonical_bytes(
            {
                **json.loads(self.recipe),
                "applicability": self.applicability,
                "state_dimensions": [asdict(s) for s in self.state_dimensions],
                "transitions": [asdict(s) for s in self.transitions],
                "capabilities": asdict(self.capabilities),
                "binding": self.binding,
                "callable_surfaces": [
                    {
                        **asdict(surface),
                        "overloads": [json.loads(item) for item in surface.overloads],
                    }
                    for surface in self.callable_surfaces
                ],
            }
        )


@dataclass(frozen=True)
class EffectiveDataOperationModel:
    version: str
    kinds: tuple[EffectiveKind, ...]
    operations: tuple[EffectiveOperation, ...]
    bindings: tuple[RelationalBinding, ...]
    nodes: tuple[SemanticNode, ...]
    edges: tuple[SemanticEdge, ...]
    implementation_slices: tuple[ImplementationSlice, ...] = ()
    identities: tuple[EffectiveIdentity, ...] = ()

    def semantic_records(self) -> dict:
        return {
            "nodes": tuple(node.record() for node in self.nodes),
            "edges": tuple(asdict(edge) for edge in self.edges),
        }

    def operation(self, semantic_id: str) -> EffectiveOperation:
        return next(
            operation for operation in self.operations if operation.semantic_id == semantic_id
        )

    @property
    def content(self) -> bytes:
        """Explicit complete export, including origins omitted by library-native dumps."""

        def encode(value):
            if isinstance(value, bytes):
                return {"json": json.loads(value)}
            if isinstance(value, dict):
                return {key: encode(item) for key, item in value.items()}
            if isinstance(value, (tuple, list)):
                return [encode(item) for item in value]
            return value

        return canonical_bytes(encode(asdict(self)))


@dataclass(frozen=True)
class BoundRoleMember:
    """Portable value/source facts plus the exact selected support episodes."""

    product: str
    kind_contract: str
    subject: str
    original_source: str
    analyzed_scope: bytes
    coverage: bytes
    support_episodes: tuple[str, ...]
    support_evidence: bytes
    position: int | None = None
    multiplicity: int = 1
    member: str | None = None
    provider_identity: str | None = None
    alternative_identity: str | None = None


@dataclass(frozen=True)
class ResolvedRoleBinding:
    role: str
    state: Literal["present", "known-absent", "unavailable", "unknown"]
    members: tuple[BoundRoleMember, ...] = ()
    population_witness: bytes | None = None
    selected_alternative: str | None = None


@dataclass(frozen=True)
class ResolvedOperationBinding:
    operation: str
    subject: str
    roles: tuple[ResolvedRoleBinding, ...]
    parameters: bytes
    inference: str
    authorization: bytes
    trust_evidence: bytes
    execution_profile: str
    replicate: str | None = None


def read_effective_data_operations(content: bytes) -> EffectiveDataOperationModel:
    """Read the archived v1 product; missing fields never acquire current defaults."""
    from dataclasses import fields, is_dataclass

    from cattrs import Converter
    from cattrs.gen import make_dict_structure_fn

    record = json.loads(content)
    if not isinstance(record, dict) or record.get("version") != MODEL_VERSION:
        raise ValueError("unsupported archived data-operation model version")
    converter = Converter(forbid_extra_keys=True)

    def structure_bytes(value, _):
        if not isinstance(value, dict) or set(value) != {"json"}:
            raise ValueError("invalid archived semantic payload")
        return canonical_bytes(value["json"])

    def structure_record(cls):
        build = make_dict_structure_fn(cls, converter, _cattrs_forbid_extra_keys=True)
        expected = {field.name for field in fields(cls)}

        def structure(value, _):
            if not isinstance(value, dict) or set(value) != expected:
                raise ValueError("incomplete archived " + cls.__name__ + " record")
            return build(value, cls)

        return structure

    converter.register_structure_hook(bytes, structure_bytes)
    converter.register_structure_hook_factory(is_dataclass, structure_record)
    return converter.structure(record, EffectiveDataOperationModel)
