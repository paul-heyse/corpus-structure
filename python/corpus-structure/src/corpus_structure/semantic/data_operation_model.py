"""Immutable compiler products for declared data operations.

Source locations and fact origins are diagnostic evidence. Semantic payloads contain
stable references and effective meaning only, before any release identity exists.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from decimal import Decimal
from typing import Literal

from .data_operation_json import json_bytes, json_loads
from .data_operation_support import (
    ComputationalSupportReference,
    OriginalSourceSupportReference,
    SupportReference,
)
from .identity import canonical_bytes

MODEL_VERSION = "data-operation-model-v4"
PREVIOUS_MODEL_VERSION = "data-operation-model-v3"
ARCHIVED_MODEL_VERSION = "data-operation-model-v2"


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
    identity_requirements: tuple[
        Literal["episode", "provider", "alternative", "original-source"], ...
    ] = ()
    source_set: str | None = None
    source_reference_field: str | None = None
    origins: tuple[Literal["computation", "original-source"], ...] = ("computation",)


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
    subject_field: str | None = None


def operation_role_record(role: OperationRole, *, result_only: bool = False) -> dict:
    """Export absent subject association under its original archived meaning."""
    record = asdict(role)
    if role.subject_field is None:
        record.pop("subject_field")
    if role.support is not None:
        support = asdict(role.support)
        for name in ("source_set", "source_reference_field"):
            if support[name] is None:
                support.pop(name)
        if result_only or role.support.origins == ("computation",):
            support.pop("origins")
        record["support"] = support
    return record


@dataclass(frozen=True)
class BindingField:
    role: str
    projection: str
    field: str


@dataclass(frozen=True)
class OutputWitnessComparison:
    output_field: str
    input: BindingField
    encoding: Literal["value", "json", "context-meaning-json"]


@dataclass(frozen=True)
class OutputWitnessGroup:
    output_role: str
    records: str
    input_role: str
    comparisons: tuple[OutputWitnessComparison, ...]


@dataclass(frozen=True)
class BindingOperand:
    """Typed value source; names resolve only in the frozen demand/projection universe."""

    kind: Literal["field", "literal", "parameter", "population"]
    value_type: str
    field: BindingField | None = None
    name: str | None = None
    value: bytes | None = None


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
        "range",
        "membership",
        "covers",
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
    operands: tuple[BindingOperand, ...] = ()
    choice_parameter: str | None = None


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
class StreamSettlement:
    mode: Literal["terminal-atomic"]
    output_role: str
    terminal_outcome: str


@dataclass(frozen=True)
class ConsumerSelectionCapability:
    entrypoint: str
    source_digest: str


@dataclass(frozen=True)
class ImplementationCapabilities:
    forms: tuple[Literal["scalar", "batch", "stream"], ...]
    preparation: str
    cancellation: str
    ownership: str
    limits: tuple[str, ...] = ()
    stream_settlement: StreamSettlement | None = None
    prepared_factory: ConsumerSelectionCapability | None = None


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
    potential_dependencies: tuple[str, ...] = ()
    result_fields: tuple[tuple[str, str], ...] = ()
    consumer_selection: ConsumerSelectionCapability | None = None
    output_witnesses: tuple[OutputWitnessGroup, ...] = ()

    @property
    def recipe(self) -> bytes:
        """Eligibility-only rules have a separate identity; support/scope remain determinants."""
        return canonical_bytes(
            {
                **({"stream_settlement": asdict(self.capabilities.stream_settlement)} if self.capabilities.stream_settlement is not None else {}),
                "id": self.semantic_id,
                "profile": self.profile,
                "subject": self.subject,
                "context": self.context,
                "roles": [operation_role_record(role, result_only=True) for role in self.roles],
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
                **({"result_fields": dict(self.result_fields)} if self.result_fields else {}),
                **({"output_witnesses": [asdict(group) for group in self.output_witnesses]} if self.output_witnesses else {}),
            }
        )

    @property
    def eligibility(self) -> bytes:
        return canonical_bytes(
            {
                "operation": self.semantic_id,
                "applicability": self.applicability,
                "binding": self.binding,
                **(
                    {
                        "support_origins": {
                            role.name: role.support.origins
                            for role in self.roles
                            if role.support is not None and role.support.origins != ("computation",)
                        }
                    }
                    if any(
                        role.support is not None and role.support.origins != ("computation",)
                        for role in self.roles
                    )
                    else {}
                ),
            }
        )

    @property
    def definition(self) -> bytes:
        return canonical_bytes(
            {
                **json.loads(self.recipe),
                "roles": [operation_role_record(role) for role in self.roles],
                "applicability": self.applicability,
                **(
                    {"potential_dependencies": self.potential_dependencies}
                    if self.potential_dependencies
                    else {}
                ),
                "state_dimensions": [asdict(s) for s in self.state_dimensions],
                "transitions": [asdict(s) for s in self.transitions],
                "capabilities": {key: value for key, value in asdict(self.capabilities).items() if value is not None},
                **({"consumer_selection": asdict(self.consumer_selection)} if self.consumer_selection is not None else {}),
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
class GraphProjectionDefinition:
    """Compiled interpretation; concrete snapshots supply selection, never new semantics."""

    name: Literal["semantic-reference", "potential-producers", "selected-dependencies"]
    source_contract: Literal["effective-semantic-records", "effective-operations"]
    node_kinds: tuple[str, ...]
    relationship_kinds: tuple[str, ...]
    orientation: Literal["owner-to-dependency"] = "owner-to-dependency"
    identity: Literal["stable-semantic-reference"] = "stable-semantic-reference"
    occurrences: Literal["typed-role-position-multiplicity"] = "typed-role-position-multiplicity"
    selection: Literal["complete-model", "explicit-producer-choices"] = "complete-model"
    snapshot: Literal["immutable-effective-model"] = "immutable-effective-model"
    unresolved: Literal["refuse"] = "refuse"
    completeness: Literal["closed-declared-universe"] = "closed-declared-universe"
    attributes: Literal["canonical-semantic-payload-unweighted"] = (
        "canonical-semantic-payload-unweighted"
    )
    analyses: tuple[str, ...] = ("root-inclusive-closure", "strong-components")

    @property
    def identity_bytes(self) -> bytes:
        return canonical_bytes(asdict(self))


def compiled_graph_projections(nodes, edges) -> tuple[GraphProjectionDefinition, ...]:
    """Derive views of the owned typed facts, not a second authored graph catalogue."""
    return (
        GraphProjectionDefinition(
            "semantic-reference",
            "effective-semantic-records",
            tuple(sorted({node.category for node in nodes})),
            tuple(sorted({edge.relation for edge in edges})),
        ),
        GraphProjectionDefinition(
            "potential-producers",
            "effective-operations",
            ("operation",),
            ("operation_dependency", "potential_operation_dependency"),
        ),
        GraphProjectionDefinition(
            "selected-dependencies",
            "effective-operations",
            ("operation",),
            ("operation_dependency", "selected_operation_dependency"),
            selection="explicit-producer-choices",
        ),
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
    graph_projections: tuple[GraphProjectionDefinition, ...] = ()

    def semantic_records(self) -> dict:
        return {
            "nodes": tuple(node.record() for node in self.nodes),
            "edges": tuple(asdict(edge) for edge in self.edges),
        }

    def projection_graph(self, name: str, *, selected_dependencies=()):
        """Construct an authenticated declared view, retaining isolates and typed occurrences."""
        from .data_operation_identity import SemanticGraph

        if self.version != MODEL_VERSION:
            raise ValueError("historical model cannot supply current projection interpretation")
        expected = compiled_graph_projections(self.nodes, self.edges)
        if self.graph_projections != expected:
            raise ValueError("missing or incompatible compiled graph projection interpretation")
        definition = next((p for p in self.graph_projections if p.name == name), None)
        if definition is None:
            raise ValueError("unknown graph projection " + name)
        choices = dict(selected_dependencies)
        if len(choices) != len(selected_dependencies):
            raise ValueError("duplicate producer selection")
        if name == "semantic-reference":
            if choices:
                raise ValueError("semantic projection does not consume producer choices")
            records = self.semantic_records()
        else:
            operations = {operation.semantic_id: operation for operation in self.operations}
            if not choices.keys() <= operations.keys():
                raise ValueError("unknown selected operation")
            if name != "selected-dependencies" and choices:
                raise ValueError("potential projection does not consume producer choices")
            selected_edges = []
            for operation in self.operations:
                selected = choices.get(operation.semantic_id, ())
                if len(set(selected)) != len(selected) or not set(selected) <= set(
                    operation.potential_dependencies
                ):
                    raise ValueError("selected dependency is outside the declared alternatives")
                for position, dependency in enumerate(operation.dependencies):
                    selected_edges.append(
                        SemanticEdge(
                            operation.semantic_id,
                            dependency,
                            "operation_dependency",
                            position=position,
                        )
                    )
                optional = (
                    operation.potential_dependencies if name == "potential-producers" else selected
                )
                relation = (
                    "potential_operation_dependency"
                    if name == "potential-producers"
                    else "selected_operation_dependency"
                )
                for position, dependency in enumerate(optional):
                    selected_edges.append(
                        SemanticEdge(operation.semantic_id, dependency, relation, position=position)
                    )
            records = {
                "nodes": tuple(node.record() for node in self.nodes if node.id in operations),
                "edges": tuple(asdict(edge) for edge in selected_edges),
            }
        return SemanticGraph(records)

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

        record = asdict(self)
        for operation in record["operations"]:
            if self.version != MODEL_VERSION:
                if operation["output_witnesses"]:
                    raise ValueError("historical models cannot declare output witnesses")
                operation.pop("consumer_selection")
                operation["capabilities"].pop("stream_settlement")
                operation["capabilities"].pop("prepared_factory")
            for role in operation["roles"]:
                if role["subject_field"] is None:
                    role.pop("subject_field")
                if role["support"] is not None:
                    for name in ("source_set", "source_reference_field"):
                        if role["support"][name] is None:
                            role["support"].pop(name)
            if not operation["output_witnesses"]:
                operation.pop("output_witnesses")
            if not operation["result_fields"]:
                operation.pop("result_fields")
        if self.version == ARCHIVED_MODEL_VERSION:
            # Retained v2 candidates retain their exact bytes, without invented projections.
            if self.graph_projections:
                raise ValueError("historical v2 cannot declare current graph projections")
            record.pop("graph_projections")
        return canonical_bytes(encode(record))


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
    support_references: tuple[SupportReference, ...] = ()

    def __post_init__(self) -> None:
        if not self.support_references and self.support_episodes:
            evidence = json.loads(self.support_evidence)
            use_id = evidence.get("use_id") if isinstance(evidence, dict) else None
            object.__setattr__(
                self,
                "support_references",
                tuple(
                    ComputationalSupportReference(
                        derivation_id=episode,
                        admission_use_id=use_id if len(self.support_episodes) == 1 else None,
                    )
                    for episode in self.support_episodes
                ),
            )
        computed = tuple(
            reference.derivation_id
            for reference in self.support_references
            if isinstance(reference, ComputationalSupportReference)
        )
        if computed != self.support_episodes or any(
            not isinstance(
                reference,
                (
                    ComputationalSupportReference,
                    OriginalSourceSupportReference,
                ),
            )
            for reference in self.support_references
        ):
            raise ValueError(
                "support episodes must be exactly the computational support projection"
            )


@dataclass(frozen=True)
class ResolvedRoleBinding:
    role: str
    state: Literal["present", "known-absent", "unavailable", "unknown", "invalid"]
    members: tuple[BoundRoleMember, ...] = ()
    population_witness: bytes | None = None
    selected_alternative: str | None = None


def json_context_meaning(content: bytes) -> bytes:
    """Canonical typed JSON meaning with JSONB-equivalent numeric semantics."""
    from .data_operation_identity import semantic_value

    return canonical_bytes(
        semantic_value(json.loads(content, parse_int=Decimal, parse_float=Decimal))
    )


@dataclass(frozen=True, eq=False)
class SubjectContext:
    """The complete immutable address of an admitted subject occurrence."""

    project_id: str
    subject: str
    original_source: str
    analyzed_scope: bytes

    def __post_init__(self):
        if not self.project_id or not self.subject or not self.original_source:
            raise ValueError("subject context requires project, subject and original source")
        object.__setattr__(self, "analyzed_scope", json_bytes(json_loads(self.analyzed_scope)))

    @property
    def record(self) -> dict:
        return {
            "project_id": self.project_id,
            "subject": self.subject,
            "original_source": self.original_source,
            "analyzed_scope": json_loads(self.analyzed_scope),
        }

    @property
    def identity_content(self) -> bytes:
        from .data_operation_identity import semantic_value

        return canonical_bytes(semantic_value(self.identity_record))

    def __eq__(self, other):
        if not isinstance(other, SubjectContext):
            return NotImplemented
        return self.identity_content == other.identity_content

    def __hash__(self):
        return hash(self.identity_content)

    @property
    def identity_record(self) -> dict:
        """JSONB scope numbers have decimal value semantics, unlike typed inputs."""
        return {
            **self.record,
            "analyzed_scope": json.loads(
                self.analyzed_scope, parse_int=Decimal, parse_float=Decimal
            ),
        }


@dataclass(frozen=True)
class ResolvedOperationBinding:
    operation: str
    subject: str
    roles: tuple[ResolvedRoleBinding, ...]
    parameters: bytes  # Canonical tagged semantic mapping; never a lossy JSON display.
    inference: str
    authorization: bytes
    trust_evidence: bytes
    execution_profile: str
    replicate: str | None = None
    source_sets: bytes = b"{}"
    subject_context: SubjectContext = field(kw_only=True)

    def __post_init__(self):
        if self.subject_context.subject != self.subject:
            raise ValueError("binding subject differs from its complete context")


def read_effective_data_operations(content: bytes) -> EffectiveDataOperationModel:
    """Read current meaning or exact retained v2 meaning; never promote old interpretation."""
    from dataclasses import fields, is_dataclass

    from cattrs import Converter
    from cattrs.gen import make_dict_structure_fn

    record = json.loads(content)
    if not isinstance(record, dict) or record.get("version") not in {
        MODEL_VERSION,
        PREVIOUS_MODEL_VERSION,
        ARCHIVED_MODEL_VERSION,
    }:
        raise ValueError("unsupported archived data-operation model version")
    archived_v2 = record["version"] == ARCHIVED_MODEL_VERSION
    historical_model = record["version"] != MODEL_VERSION
    converter = Converter(forbid_extra_keys=True, detailed_validation=False)

    def structure_bytes(value, _):
        if not isinstance(value, dict) or set(value) != {"json"}:
            raise ValueError("invalid archived semantic payload")
        return canonical_bytes(value["json"])

    def structure_record(cls):
        build = make_dict_structure_fn(cls, converter, _cattrs_forbid_extra_keys=True)
        expected = {field.name for field in fields(cls)}
        historical = (
            {"graph_projections": []} if cls is EffectiveDataOperationModel and archived_v2 else {}
        )
        if historical_model and cls is ImplementationCapabilities:
            historical["stream_settlement"] = None
            historical["prepared_factory"] = None
        if historical_model and cls is EffectiveOperation:
            historical["consumer_selection"] = None
        archived_fields = expected - historical.keys()

        def structure(value, _):
            if cls is InputSupport and isinstance(value, dict):
                value = {
                    "source_set": None,
                    "source_reference_field": None,
                    "origins": ["computation"],
                    **value,
                }
            if cls is OperationRole and isinstance(value, dict):
                value = {"subject_field": None, **value}
            if cls is EffectiveOperation and isinstance(value, dict):
                if historical_model and value.get("output_witnesses"):
                    raise ValueError("historical models cannot declare output witnesses")
                value = {"result_fields": [], "output_witnesses": [], **value}
            if not isinstance(value, dict) or set(value) != archived_fields:
                raise ValueError("incomplete archived " + cls.__name__ + " record")
            return build({**value, **historical}, cls)

        return structure

    converter.register_structure_hook(bytes, structure_bytes)
    converter.register_structure_hook_factory(is_dataclass, structure_record)
    return converter.structure(record, EffectiveDataOperationModel)
