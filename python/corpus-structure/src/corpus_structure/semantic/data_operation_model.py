"""Immutable compiler products for declared data operations.

Source locations and fact origins are diagnostic evidence. Semantic payloads contain
stable references and effective meaning only, before any release identity exists.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from decimal import Decimal
from functools import cached_property, lru_cache
from typing import Literal, get_args, get_type_hints

from .data_operation_json import json_bytes, json_loads
from .data_operation_support import (
    AuthoredFactSupportReference,
    ComputationalSupportReference,
    OriginalSourceSupportReference,
    SupportReference,
)
from .data_operation_version import MODEL_VERSION
from .identity import canonical_bytes
from .selected_support import ProducerOutputOccurrence
from .types import Diagnostic

SubjectScope = Literal[
    "original-source", "original-document", "selected-source-set", "project", "invocation"
]


ReplicatePolicy = Literal[
    "deterministic-single-result", "retained-observation-single-result", "explicit-replicates"
]


def validate_replicate_selection(policy, replicate, *, owner):
    """A retained value is reusable without promising a fresh bitwise-equivalent sample."""
    if policy not in get_args(ReplicatePolicy):
        raise ValueError("unsupported replicate policy for " + owner)
    if policy == "explicit-replicates":
        if type(replicate) is not str or not replicate:
            raise ValueError("explicit replicate selection is required for " + owner)
    elif replicate is not None:
        if policy == "retained-observation-single-result":
            raise ValueError(
                "fresh independent replication is unsupported for retained observation " + owner
            )
        raise ValueError("deterministic operation cannot select a replicate: " + owner)


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
class InputCoverage:
    """Checked role reference; the relational binding owns selected input coverage."""

    role: str
    description: str


@dataclass(frozen=True)
class InputSupport:
    provenance: Literal["exact", "value_substitution"]
    source: str
    coverage: InputCoverage
    authorization: tuple[str, ...] = ()
    closure: tuple[str, ...] = ()
    identity_requirements: tuple[
        Literal["episode", "provider", "alternative", "original-source"], ...
    ] = ()
    source_set: str | None = None
    origins: tuple[Literal["computation", "original-source", "authored"], ...] = ("computation",)


@dataclass(frozen=True)
class ProducerRequirement:
    """The consuming role's required authenticated producer properties."""

    output_role: str | None
    requires_cpu: bool
    required_effect: str | None
    required_family: str


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
    subject_target: Literal["subject", "original-source", "source-set"] = "subject"
    producer_requirement: ProducerRequirement | None = None


def operation_role_record(role: OperationRole, *, result_only: bool = False) -> dict:
    """Export absent subject association under its original archived meaning."""
    record = asdict(role)
    if role.producer_requirement is None:
        record.pop("producer_requirement")
    if role.subject_target == "subject":
        record.pop("subject_target")
    if role.subject_field is None:
        record.pop("subject_field")
    if role.support is not None:
        support = asdict(role.support)
        support["coverage"] = {"role": role.support.coverage.role}
        for name in ("source_set",):
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
    population_projection: Literal["member", "qualified-context"] = "member"


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
    semantic_digest: str

    @property
    def semantic_record(self) -> dict:
        return {"entrypoint": self.entrypoint, "semantic_digest": self.semantic_digest}


@dataclass(frozen=True)
class ImplementationCapabilities:
    forms: tuple[Literal["scalar", "batch", "stream"], ...]
    preparation: str
    cancellation: str
    ownership: str
    limits: tuple[str, ...] = ()
    stream_settlement: StreamSettlement | None = None
    prepared_factory: ConsumerSelectionCapability | None = None
    cpu_receipts: int | None = None


@dataclass(frozen=True)
class OpaqueBoundary:
    reference: str
    contract: str
    role: str
    content_digest: str | None = None
    reuse_eligible: bool = field(default=True, kw_only=True)


@dataclass(frozen=True)
class SourceUnknown:
    source: str
    location: str
    reason: str
    required: bool = True


@dataclass(frozen=True)
class ImplementationReferenceFact:
    source: str
    target: str
    relation: str
    location: str
    supplying_owner: str
    provenance: Literal["closed-source-structural"] = "closed-source-structural"


@dataclass(frozen=True)
class ImplementationSlice:
    root: str
    nodes: tuple[SemanticNode, ...]
    edges: tuple[SemanticEdge, ...]
    boundaries: tuple[OpaqueBoundary, ...] = ()
    unknowns: tuple[SourceUnknown, ...] = ()
    normalization: str = "python-cst-v1"
    references: tuple[ImplementationReferenceFact, ...] = ()

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


@dataclass(frozen=True)
class ExternalExecutorContract:
    version: Literal["external-executor-v1"]
    instructions: str
    requested_actor: str
    requested_model: str | None
    reference_scope: Literal["declared-inputs-only"]


@dataclass(frozen=True)
class SubjectDefinition:
    """Nominal subject meaning, separate from its concrete occurrence address."""

    semantic_id: str
    identifier_kind: str
    scope: SubjectScope


@dataclass(frozen=True)
class EnforcementClaim:
    """Documentation, or a checked existing semantic enforcement owner."""

    kind: Literal["documentation", "binding", "schema", "implementation", "native-admission"]
    text: str | None = None
    reference: str | None = None
    interpretation: str | None = None
    parameters: bytes = b"{}"
    semantics: bytes = b"null"

    def __post_init__(self):
        if self.kind == "documentation":
            if (
                not self.text
                or self.reference is not None
                or self.interpretation is not None
                or self.parameters != b"{}"
                or self.semantics != b"null"
            ):
                raise ValueError("documentation cannot claim executable enforcement")
        elif (
            self.text is not None
            or not self.reference
            or not self.interpretation
            or json.loads(self.parameters) != {}
        ):
            raise ValueError("checked enforcement requires its exact owner and interpretation")

    @property
    def semantic_record(self) -> dict | None:
        if self.kind == "documentation":
            return None
        return {
            "kind": self.kind,
            "reference": self.reference,
            "interpretation": self.interpretation,
            "parameters": json.loads(self.parameters),
            "semantics": json.loads(self.semantics),
        }


def enforced_claims(claims: tuple[EnforcementClaim, ...], *, definition_only=False) -> list[dict]:
    records = []
    for claim in claims:
        record = claim.semantic_record
        if record is not None:
            if definition_only and claim.kind == "implementation":
                record.pop("semantics")
            records.append(record)
    return records


@dataclass(frozen=True)
class NumericalPolicyReference:
    """A typed numerical body selected from an exact captured semantic asset."""

    kind: str
    asset: str
    content_digest: str
    pointer: str
    body: bytes

    @property
    def record(self) -> dict:
        return {
            "kind": self.kind,
            "asset": self.asset,
            "content_digest": self.content_digest,
            "pointer": self.pointer,
            "body": json.loads(self.body),
        }


@dataclass(frozen=True)
class CoverageResultOwner:
    kind: Literal["implementation", "native-admission", "declared-contract", "schema"]
    reference: str
    interpretation: str
    semantics: bytes

    @property
    def record(self):
        return {
            "kind": self.kind,
            "reference": self.reference,
            "interpretation": self.interpretation,
            "semantics": json.loads(self.semantics),
        }


@dataclass(frozen=True)
class CoverageContract:
    """Actual selection and result owners, with descriptive claims kept separate."""

    binding: str
    selection: bytes
    result_selection: bytes
    result_owners: tuple[CoverageResultOwner, ...]
    description: str

    def record(self, *, result_only=False, definition_only=False):
        return {
            "binding": self.binding,
            "selection": json.loads(self.result_selection if result_only else self.selection),
            "result_owners": [
                {
                    key: value
                    for key, value in owner.record.items()
                    if not (
                        definition_only
                        and owner.kind in {"implementation", "native-admission"}
                        and key == "semantics"
                    )
                }
                for owner in self.result_owners
            ],
        }


@dataclass(frozen=True)
class ValidityClaim:
    families: tuple[str, ...] = ()
    conservative: bool = True


@dataclass(frozen=True)
class EffectiveOperation:
    semantic_id: str
    profile: Literal["derivation", "discovery", "selection", "command", "read"]
    subject: str
    context: tuple[str, ...]
    roles: tuple[OperationRole, ...]
    applicability: tuple[EnforcementClaim, ...]
    invariants: tuple[EnforcementClaim, ...]
    coverage: CoverageContract
    outcomes: tuple[str, ...]
    precision_description: str | None
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
    replicate_policy: ReplicatePolicy = "deterministic-single-result"
    support_policy: str = "all-declared-input-support"
    potential_dependencies: tuple[str, ...] = ()
    result_fields: tuple[tuple[str, str], ...] = ()
    consumer_selection: ConsumerSelectionCapability | None = None
    output_witnesses: tuple[OutputWitnessGroup, ...] = ()
    external: ExternalExecutorContract | None = None
    discovery_relation: Literal["role-associated", "subject-population"] = field(kw_only=True)
    numerical_policy: NumericalPolicyReference | None = field(default=None, kw_only=True)
    validity: ValidityClaim = field(default_factory=ValidityClaim, kw_only=True)

    @property
    def recipe(self) -> bytes:
        """Eligibility-only rules have a separate identity; support/scope remain determinants."""
        return canonical_bytes(
            {
                **(
                    {"stream_settlement": asdict(self.capabilities.stream_settlement)}
                    if self.capabilities.stream_settlement is not None
                    else {}
                ),
                "id": self.semantic_id,
                **({"external": asdict(self.external)} if self.external is not None else {}),
                "profile": self.profile,
                "subject": self.subject,
                "discovery_relation": self.discovery_relation,
                "context": self.context,
                "roles": [operation_role_record(role, result_only=True) for role in self.roles],
                "invariants": enforced_claims(self.invariants),
                "coverage": self.coverage.record(result_only=True),
                "outcomes": self.outcomes,
                **(
                    {"numerical_policy": self.numerical_policy.record}
                    if self.numerical_policy is not None
                    else {}
                ),
                "dependencies": self.dependencies,
                **({"behavior": self.behavior} if self.implementation_root is None else {}),
                "parameters": json.loads(self.parameters),
                "assets": [asdict(a) for a in self.assets],
                "effects": [asdict(effect) for effect in self.effects],
                "replicate_policy": self.replicate_policy,
                "support_policy": self.support_policy,
                **({"result_fields": dict(self.result_fields)} if self.result_fields else {}),
                **(
                    {"output_witnesses": [asdict(group) for group in self.output_witnesses]}
                    if self.output_witnesses
                    else {}
                ),
            }
        )

    @property
    def eligibility(self) -> bytes:
        return canonical_bytes(
            {
                "operation": self.semantic_id,
                "applicability": enforced_claims(self.applicability),
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
                "validity": asdict(self.validity),
                "roles": [operation_role_record(role) for role in self.roles],
                "coverage": self.coverage.record(definition_only=True),
                "invariants": enforced_claims(self.invariants, definition_only=True),
                "applicability": enforced_claims(self.applicability, definition_only=True),
                **(
                    {"potential_dependencies": self.potential_dependencies}
                    if self.potential_dependencies
                    else {}
                ),
                "state_dimensions": [asdict(s) for s in self.state_dimensions],
                "transitions": [asdict(s) for s in self.transitions],
                "capabilities": {
                    key: (
                        self.capabilities.prepared_factory.semantic_record
                        if key == "prepared_factory"
                        and self.capabilities.prepared_factory is not None
                        else value
                    )
                    for key, value in asdict(self.capabilities).items()
                    if value is not None
                },
                **(
                    {"consumer_selection": self.consumer_selection.semantic_record}
                    if self.consumer_selection is not None
                    else {}
                ),
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

    name: Literal[
        "semantic-reference",
        "potential-producers",
        "selected-dependencies",
        "bound-requests",
        "selected-support",
        "source-hierarchy",
        "assessment",
        "task-assessment",
        "lexical-reference",
        "possible-call",
        "resolved-definition",
        "type-reference",
        "implementation-determinant",
    ]
    source_contract: Literal[
        "effective-semantic-records",
        "effective-operations",
        "selected-native-records",
        "selected-source-records",
        "protected-assessment-records",
        "selected-characterization-records",
        "captured-implementation-records",
    ]
    node_kinds: tuple[str, ...]
    relationship_kinds: tuple[str, ...]
    orientation: Literal["owner-to-dependency", "parent-to-child", "assertion-incidence"] = (
        "owner-to-dependency"
    )
    identity: Literal["stable-semantic-reference", "qualified-native-reference"] = (
        "stable-semantic-reference"
    )
    occurrences: Literal["typed-role-position-multiplicity"] = "typed-role-position-multiplicity"
    selection: Literal[
        "complete-model",
        "explicit-producer-choices",
        "pinned-native-cut",
        "protected-question-and-prediction",
    ] = "complete-model"
    snapshot: Literal["immutable-effective-model", "native-read-and-trust", "captured-source"] = (
        "immutable-effective-model"
    )
    unresolved: Literal["refuse", "explicit-unknown-boundary"] = "refuse"
    completeness: Literal["closed-declared-universe", "explicit-examined-universe"] = (
        "closed-declared-universe"
    )
    attributes: Literal[
        "canonical-semantic-payload-unweighted",
        "typed-native-occurrences-unweighted",
        "protected-asymmetric-fields",
    ] = "canonical-semantic-payload-unweighted"
    analyses: tuple[str, ...] = (
        "members",
        "root-inclusive-closure",
        "strong-components",
        "witness-path",
        "scope-boundary",
        "dependency-order",
    )

    @property
    def identity_bytes(self) -> bytes:
        return canonical_bytes(asdict(self))


def compiled_graph_projections(
    nodes, edges, implementation_slices=()
) -> tuple[GraphProjectionDefinition, ...]:
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
        *compiled_snapshot_projections(implementation_slices),
    )


def compiled_snapshot_projections(
    implementation_slices=(),
) -> tuple[GraphProjectionDefinition, ...]:
    """Interpret the owned native/source/assessment protocols, never selected facts.

    Native row and reference contracts own occurrence roles; these profiles bind their
    supported graph interpretation into each release. Concrete cuts are acquired later.
    """
    implementation_kinds = tuple(
        sorted(
            {node.category for item in implementation_slices for node in item.nodes}
            | {"lexical-reference", "unresolved-reference"}
        )
    )
    determinant_relations = tuple(
        sorted({edge.relation for item in implementation_slices for edge in item.edges})
    )
    from .assessment_graph_contract import (
        ASSESSMENT_NODE_KINDS,
        ASSESSMENT_RELATION_KINDS,
        TASK_ASSESSMENT_NODE_KINDS,
        TASK_ASSESSMENT_RELATION_KINDS,
    )

    def native(
        name: Literal[
            "bound-requests",
            "selected-support",
            "source-hierarchy",
            "assessment",
            "task-assessment",
        ],
        nodes: tuple[str, ...],
        relationships: tuple[str, ...],
        *,
        source: Literal[
            "selected-native-records",
            "selected-source-records",
            "protected-assessment-records",
            "selected-characterization-records",
        ] = "selected-native-records",
        orientation: Literal[
            "owner-to-dependency", "parent-to-child", "assertion-incidence"
        ] = "owner-to-dependency",
        selection: Literal[
            "pinned-native-cut", "protected-question-and-prediction"
        ] = "pinned-native-cut",
        attributes: Literal[
            "typed-native-occurrences-unweighted", "protected-asymmetric-fields"
        ] = "typed-native-occurrences-unweighted",
    ):
        return GraphProjectionDefinition(
            name,
            source,
            nodes,
            relationships,
            orientation=orientation,
            identity="qualified-native-reference",
            selection=selection,
            snapshot="native-read-and-trust",
            unresolved="explicit-unknown-boundary",
            completeness="explicit-examined-universe",
            attributes=attributes,
            analyses=(
                "members",
                "root-inclusive-closure",
                "strong-components",
                "witness-path",
                "scope-boundary",
                "dependency-order",
            ),
        )

    return (
        native(
            "bound-requests",
            ("request", "obligation", "use", "population", "authority"),
            ("selected-input", "requires", "population"),
        ),
        native(
            "selected-support",
            (
                "product",
                "member",
                "episode",
                "use",
                "population",
                "original",
                "authored",
                "authority",
            ),
            ("input", "output", "support", "admission", "population"),
        ),
        native(
            "source-hierarchy",
            ("source", "record", "member"),
            ("contains",),
            source="selected-source-records",
            orientation="parent-to-child",
        ),
        native(
            "assessment",
            ASSESSMENT_NODE_KINDS,
            ASSESSMENT_RELATION_KINDS,
            source="selected-characterization-records",
        ),
        native(
            "task-assessment",
            TASK_ASSESSMENT_NODE_KINDS,
            TASK_ASSESSMENT_RELATION_KINDS,
            source="protected-assessment-records",
            orientation="assertion-incidence",
            selection="protected-question-and-prediction",
            attributes="protected-asymmetric-fields",
        ),
        *(
            GraphProjectionDefinition(
                name,
                "captured-implementation-records",
                implementation_kinds,
                relations,
                snapshot="captured-source",
                unresolved="explicit-unknown-boundary",
                completeness="explicit-examined-universe",
                analyses=(
                    "members",
                    "root-inclusive-closure",
                    "strong-components",
                    "witness-path",
                    "scope-boundary",
                    "dependency-order",
                ),
            )
            for name, relations in (
                ("lexical-reference", ("lexical_reference",)),
                ("possible-call", ("possible_call",)),
                ("resolved-definition", ("resolved_definition",)),
                ("type-reference", ("type_reference",)),
                ("implementation-determinant", determinant_relations),
            )
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
    subject_definitions: tuple[SubjectDefinition, ...] = ()

    source_interfaces: bytes | None = field(default=None, repr=False, compare=False)
    diagnostics: tuple[Diagnostic, ...] = field(default=(), repr=False, compare=False)

    def semantic_records(self) -> dict:
        return {
            "nodes": tuple(node.record() for node in self.nodes),
            "edges": tuple(asdict(edge) for edge in self.edges),
        }

    def projection_definition(self, name: str) -> GraphProjectionDefinition:
        if self.version != MODEL_VERSION or self.graph_projections != compiled_graph_projections(
            self.nodes, self.edges, self.implementation_slices
        ):
            raise ValueError("missing or incompatible compiled graph projection interpretation")
        definition = next((p for p in self.graph_projections if p.name == name), None)
        if definition is None:
            raise ValueError("unknown graph projection " + name)
        return definition

    @cached_property
    def _semantic_reference_graph(self):
        return self._build_projection_graph("semantic-reference")

    @cached_property
    def _potential_producers_graph(self):
        return self._build_projection_graph("potential-producers")

    @cached_property
    def _selected_dependencies_graph(self):
        return self._build_projection_graph("selected-dependencies")

    def projection_graph(self, name: str, *, selected_dependencies=()):
        held = {
            "semantic-reference": "_semantic_reference_graph",
            "potential-producers": "_potential_producers_graph",
            "selected-dependencies": "_selected_dependencies_graph",
        }
        if not selected_dependencies and name in held:
            return getattr(self, held[name])
        return self._build_projection_graph(name, selected_dependencies=selected_dependencies)

    def _build_projection_graph(self, name: str, *, selected_dependencies=()):
        """Construct an authenticated declared view, retaining isolates and typed occurrences."""
        from .data_operation_identity import SemanticGraph

        if self.version != MODEL_VERSION:
            raise ValueError("historical model cannot supply current projection interpretation")
        expected = compiled_graph_projections(self.nodes, self.edges, self.implementation_slices)
        if self.graph_projections != expected:
            raise ValueError("missing or incompatible compiled graph projection interpretation")
        definition = next((p for p in self.graph_projections if p.name == name), None)
        if definition is None:
            raise ValueError("unknown graph projection " + name)
        if name not in {"semantic-reference", "potential-producers", "selected-dependencies"}:
            raise ValueError("snapshot projection requires authenticated source acquisition")
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

    def subject_definition(self, semantic_id: str) -> SubjectDefinition:
        definitions = [item for item in self.subject_definitions if item.semantic_id == semantic_id]
        if len(definitions) != 1:
            raise ValueError("operation requires one resolved subject definition")
        return definitions[0]

    def operation(self, semantic_id: str) -> EffectiveOperation:
        return next(
            operation for operation in self.operations if operation.semantic_id == semantic_id
        )

    @cached_property
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
        record.pop("source_interfaces")
        record.pop("diagnostics")
        if self.version != MODEL_VERSION:
            raise ValueError(
                "unsupported data-operation model version; regenerate target-native data"
            )

        def binding_record(node):
            for operand in node["operands"]:
                mode = operand["population_projection"]
                if mode == "member":
                    operand.pop("population_projection")
            for child in node["children"]:
                binding_record(child)

        for binding in record["bindings"]:
            binding_record(binding["expression"])
        for operation in record["operations"]:
            if operation["external"] is None:
                operation.pop("external")
            for role in operation["roles"]:
                if role["producer_requirement"] is None:
                    role.pop("producer_requirement")
                if role["subject_target"] == "subject":
                    role.pop("subject_target")
                if role["subject_field"] is None:
                    role.pop("subject_field")
                if role["support"] is not None:
                    for name in ("source_set",):
                        if role["support"][name] is None:
                            role["support"].pop(name)
            if not operation["output_witnesses"]:
                operation.pop("output_witnesses")
            if not operation["result_fields"]:
                operation.pop("result_fields")
        if any(type(identity) is not EffectiveIdentity for identity in self.identities):
            raise ValueError("effective identities require compact current headers")
        return canonical_bytes(encode(record))


@dataclass(frozen=True)
class BoundRoleMember:
    """Portable value/source facts plus the exact selected support episodes."""

    product: str
    kind_contract: str
    subject: str
    original_source: str | None
    analyzed_scope: bytes
    coverage: bytes
    subject_definition: str = field(kw_only=True)
    support_episodes: tuple[str, ...]
    support_evidence: bytes
    position: int | None = None
    multiplicity: int = 1
    member: str | None = None
    provider_identity: str | None = None
    alternative_identity: str | None = None
    support_references: tuple[SupportReference, ...] = field(kw_only=True)
    producer_output: ProducerOutputOccurrence | None = field(kw_only=True, default=None)

    def __post_init__(self) -> None:
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
                    AuthoredFactSupportReference,
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
    from .data_operation_values import semantic_value

    return canonical_bytes(
        semantic_value(json.loads(content, parse_int=Decimal, parse_float=Decimal))
    )


@dataclass(frozen=True, eq=False)
class SubjectContext:
    """The complete immutable address of an admitted subject occurrence."""

    project_id: str
    subject: str
    original_source: str | None
    analyzed_scope: bytes
    subject_definition: str = field(kw_only=True)

    def __post_init__(self):
        if type(self.subject_definition) is not str or not self.subject_definition:
            raise ValueError("subject context requires a subject definition")
        if (
            type(self.project_id) is not str
            or not self.project_id
            or type(self.subject) is not str
            or not self.subject
        ):
            raise ValueError("subject context requires project and subject")
        if self.original_source is not None and (
            type(self.original_source) is not str or not self.original_source
        ):
            raise ValueError(
                "subject context original source must be explicit null or a nonempty string"
            )
        object.__setattr__(self, "analyzed_scope", json_bytes(json_loads(self.analyzed_scope)))

    @property
    def record(self) -> dict:
        return {
            "project_id": self.project_id,
            "subject_definition": self.subject_definition,
            "subject": self.subject,
            "original_source": self.original_source,
            "analyzed_scope": json_loads(self.analyzed_scope),
        }

    @property
    def identity_content(self) -> bytes:
        from .data_operation_values import semantic_value

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


def validate_subject_source(
    model: EffectiveDataOperationModel, subject_definition: str, original_source: str | None
) -> None:
    """Apply the checked subject's source relation; a context shape grants no permission."""
    definition = model.subject_definition(subject_definition)
    if definition.scope not in get_args(SubjectScope):
        raise ValueError("unsupported checked subject scope")
    if original_source is None:
        if definition.scope != "project":
            raise ValueError("only a checked project-scoped subject can omit an original source")
    elif type(original_source) is not str or not original_source:
        raise ValueError("subject requires explicit null or a nonempty original source")


def validate_subject_context(
    model: EffectiveDataOperationModel,
    context: SubjectContext,
    *,
    subject_definition: str | None = None,
) -> None:
    if subject_definition is not None and context.subject_definition != subject_definition:
        raise ValueError("subject definition differs from checked operation")
    validate_subject_source(model, context.subject_definition, context.original_source)


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
    """Reuse pure strict decoding of identical ordinary immutable captured bytes."""
    if type(content) is bytes:
        return _read_effective_data_operations_cached(content)
    return _read_effective_data_operations(content)


@lru_cache(maxsize=8)
def _read_effective_data_operations_cached(content: bytes) -> EffectiveDataOperationModel:
    return _read_effective_data_operations(content)


def _read_effective_data_operations(content: bytes) -> EffectiveDataOperationModel:
    """Read the supported target-native model; old encodings require regeneration."""
    record = json.loads(content)
    if not isinstance(record, dict) or record.get("version") != MODEL_VERSION:
        raise ValueError("unsupported data-operation model version; regenerate target-native data")
    return _effective_model_structure()(record, EffectiveDataOperationModel)


@lru_cache(maxsize=1)
def _effective_model_structure():
    """Prepare one private strict conversion protocol for the current archive format."""
    from dataclasses import fields, is_dataclass
    from typing import get_origin

    from cattrs import Converter
    from cattrs.cols import homogenous_tuple_structure_factory
    from cattrs.gen import make_dict_structure_fn

    converter = Converter(forbid_extra_keys=True, detailed_validation=False)

    def exact_primitive(value, expected):
        if type(value) is not expected:
            raise TypeError("expected " + expected.__name__)
        return value

    # Generated record hooks capture their subordinate hooks. Configure the
    # complete primitive and collection policy before generating any record.
    for primitive in (str, int, bool, float):
        converter.register_structure_hook(primitive, exact_primitive)

    def tuple_hook(target):
        args = get_args(target)
        nested = (
            homogenous_tuple_structure_factory(target, converter)
            if args and args[-1] is Ellipsis
            else converter.gen_structure_hetero_tuple(target)
        )

        def structure(value, expected=target):
            if type(value) is not list:
                raise TypeError("expected archived array")
            return nested(value, expected)

        return structure

    converter.register_structure_hook_factory(lambda t: get_origin(t) is tuple, tuple_hook)

    def structure_bytes(value, _):
        if not isinstance(value, dict) or set(value) != {"json"}:
            raise ValueError("invalid archived semantic payload")
        return canonical_bytes(value["json"])

    def structure_record(cls):
        build = make_dict_structure_fn(cls, converter, _cattrs_forbid_extra_keys=True)
        expected = {field.name for field in fields(cls)}
        omitted = (
            {"source_interfaces": None, "diagnostics": []}
            if cls is EffectiveDataOperationModel
            else {}
        )
        archived_fields = expected - omitted.keys()

        def structure(value, _):
            if cls is BindingOperand and isinstance(value, dict):
                value = {"population_projection": "member", **value}
            if cls is InputSupport and isinstance(value, dict):
                value = {
                    "source_set": None,
                    "origins": ["computation"],
                    **value,
                }
            if cls is OperationRole and isinstance(value, dict):
                value = {"subject_field": None, "subject_target": "subject", "producer_requirement": None, **value}
            if cls is EffectiveOperation and isinstance(value, dict):
                value = {"external": None, "result_fields": [], "output_witnesses": [], **value}
            if not isinstance(value, dict) or set(value) != archived_fields:
                raise ValueError("incomplete archived " + cls.__name__ + " record")
            return build({**value, **omitted}, cls)

        return structure

    converter.register_structure_hook(bytes, structure_bytes)
    converter.register_structure_hook_factory(is_dataclass, structure_record)
    return converter.get_structure_hook(EffectiveDataOperationModel)


def _check_declared_literal_copies() -> None:
    from corpus_structure.schema.operation_declarations import check_literal_members

    check_literal_members("Profile", get_type_hints(EffectiveOperation)["profile"])
    check_literal_members("Form", get_args(get_type_hints(ImplementationCapabilities)["forms"])[0])
    check_literal_members("RoleDirection", get_type_hints(OperationRole)["direction"])
    check_literal_members("BindingOperator", get_type_hints(BindingExpression)["operator"])


_check_declared_literal_copies()
