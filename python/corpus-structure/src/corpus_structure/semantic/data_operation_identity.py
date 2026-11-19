"""DDO-02 pure canonical identities over effective, release-independent facts.

This versioned framing deliberately does not change ``identity.canonical_bytes`` or
any installed key ABI. Inputs are archived bytes, not live views of caller objects.
Graph edges point from an owner to its dependency. Connectivity is a derived index;
the typed records, including parallel roles, determine canonical graph meaning.
"""

from __future__ import annotations

import json
import re
from collections.abc import Iterable, Mapping
from dataclasses import dataclass, field
from hashlib import sha256
from types import MappingProxyType
from typing import TYPE_CHECKING, Any, Literal

from .data_operation_model import SubjectContext
from .data_operation_values import CollectionValue, OptionalValue, semantic_value
from .identity import canonical_bytes

if TYPE_CHECKING:
    from .graph_runtime import nx

ENCODING_VERSION = "1"


def semantic_fields(fields: Iterable[tuple[str, Any]]) -> dict[str, Any]:
    """Resolve already-qualified semantic fields, refusing aliases before dict creation."""
    result = {}
    for name, value in fields:
        _identifier(name, "semantic field")
        if name in result:
            raise ValueError(f"duplicate semantic field {name!r}")
        result[name] = value
    return result


def _identifier(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value:
        raise ValueError(f"{label} requires a nonempty string")
    return value


@dataclass(frozen=True)
class CanonicalIdentity:
    """The exact domain/version-tagged input and its full SHA-256 identity."""

    domain: str
    canonical_input: bytes
    digest: str = field(init=False)

    def __post_init__(self) -> None:
        object.__setattr__(self, "digest", sha256(self.canonical_input).hexdigest())

    @property
    def key(self) -> str:
        return f"{self.domain}:{self.digest}"


def canonical_identity(domain: str, value: Any) -> CanonicalIdentity:
    _identifier(domain, "identity domain")
    encoded = canonical_bytes(["ddo", domain, ENCODING_VERSION, semantic_value(value)])
    return CanonicalIdentity(domain, encoded)


@dataclass(frozen=True)
class SemanticEdge:
    source: str
    target: str
    relation: str
    role: str = ""
    position: int | None = None
    multiplicity: int = 1

    def record(self) -> dict[str, Any]:
        return {
            "source": self.source,
            "target": self.target,
            "relation": self.relation,
            "role": self.role,
            "position": self.position,
            "multiplicity": self.multiplicity,
        }


class SemanticGraph:
    """Validated finite effective graph with immutable payload snapshots.

    Every endpoint is authenticated before NetworkX sees an edge. All declared nodes,
    including isolates, are added. Edge occurrences are retained independently of the
    simple connectivity projection; equal occurrences retain their multiplicity too.
    """

    def __init__(
        self,
        records: Mapping[str, Any],
        *,
        iteration_components: Iterable[Iterable[str]] = (),
    ) -> None:
        from .graph_runtime import nx

        self._nodes: dict[str, tuple[str, bytes]] = {}
        for node in records["nodes"]:
            name = _identifier(node["id"], "semantic node id")
            if name in self._nodes:
                raise ValueError(f"duplicate semantic node {name!r}")
            category = _identifier(node["category"], f"node {name} category")
            self._nodes[name] = (category, canonical_bytes(semantic_value(node["payload"])))
        edges = []
        for row in records["edges"]:
            edge = SemanticEdge(**row)
            for endpoint in (edge.source, edge.target):
                if endpoint not in self._nodes:
                    raise ValueError(f"unresolved semantic edge endpoint {endpoint!r}")
            _identifier(edge.relation, "semantic edge relation")
            if not isinstance(edge.role, str):
                raise ValueError("semantic edge role must be a string")
            if edge.position is not None and (type(edge.position) is not int or edge.position < 0):
                raise ValueError("semantic edge position must be a nonnegative integer")
            if type(edge.multiplicity) is not int or edge.multiplicity < 1:
                raise ValueError("semantic edge multiplicity must be a positive integer")
            edges.append(edge)
        self._edges = tuple(sorted(edges, key=lambda edge: canonical_bytes(edge.record())))
        graph = nx.DiGraph(backend="networkx")
        graph.add_nodes_from(sorted(self._nodes))
        relations_by_pair = {}
        for edge in self._edges:
            pair = edge.source, edge.target
            relations_by_pair.setdefault(pair, set()).add(edge.relation)
        graph.add_edges_from(
            (source, target, {"relations": frozenset(relations)})
            for (source, target), relations in relations_by_pair.items()
        )
        self._graph = nx.freeze(graph)
        self.require_acyclic({"inherits"})
        self.require_acyclic({"operation_dependency"}, iteration_components=iteration_components)

    @property
    def node_ids(self) -> tuple[str, ...]:
        return tuple(sorted(self._nodes))

    @property
    def edges(self) -> tuple[SemanticEdge, ...]:
        return self._edges

    def closure(
        self,
        roots: Iterable[str],
        *,
        direction: Literal["dependencies", "dependents"] = "dependencies",
    ) -> tuple[str, ...]:
        from .graph_topology import rooted_closure

        if direction not in {"dependencies", "dependents"}:
            raise ValueError(f"unknown graph direction {direction!r}")
        roots = tuple(roots)
        for root in roots:
            if root not in self._nodes:
                raise ValueError(f"unknown semantic root {root!r}")
        return tuple(sorted(rooted_closure(self._graph, roots, reverse=direction == "dependents")))

    def direct_dependencies(self, owner: str) -> tuple[str, ...]:
        if owner not in self._nodes:
            raise ValueError("unknown semantic root " + owner)
        return tuple(sorted(self._graph.successors(owner)))

    def _projection(self, relations: set[str] | None) -> nx.DiGraph:
        from .graph_runtime import nx

        if relations is None:
            return self._graph
        selected = frozenset(relations)
        return nx.subgraph_view(
            self._graph,
            filter_edge=lambda source, target: bool(
                self._graph.edges[source, target]["relations"] & selected
            ),
        )

    def components(self, relations: set[str] | None = None) -> tuple[tuple[str, ...], ...]:
        from .graph_topology import strong_components

        return tuple(
            sorted(
                tuple(sorted(component))
                for component in strong_components(self._projection(relations))
            )
        )

    def cyclic_components(self, relations: set[str] | None = None) -> tuple[tuple[str, ...], ...]:
        from .graph_topology import cyclic_components

        return tuple(
            sorted(
                tuple(sorted(component))
                for component in cyclic_components(self._projection(relations))
            )
        )

    def require_acyclic(
        self,
        relations: set[str],
        *,
        iteration_components: Iterable[Iterable[str]] = (),
    ) -> None:
        """Only explicitly admitted complete execution SCCs can carry iteration."""
        allowed = {tuple(sorted(component)) for component in iteration_components}
        cycles = self.cyclic_components(relations)
        invalid = [component for component in cycles if component not in allowed]
        if invalid:
            raise ValueError(f"unsupported cycle in {sorted(relations)!r}: {invalid!r}")
        if allowed.difference(cycles):
            raise ValueError("iteration contract must name an actual complete cyclic component")

    def dependency_order(self) -> tuple[str, ...]:
        """Prerequisites first; recursive reference graphs have no such order."""
        from .graph_runtime import nx
        from .graph_topology import ordered_nodes

        try:
            return ordered_nodes(self._graph, reverse=True, key=str)
        except nx.NetworkXUnfeasible as exc:
            raise ValueError("cyclic graph has no dependency order") from exc

    def rooted_record(self, root: str) -> dict[str, Any]:
        selected = set(self.closure((root,)))
        # Payloads are already encoded with the exact codec; decode only the immutable
        # captured bytes, never caller-owned mutable values.
        return {
            "root": root,
            "nodes": [
                {
                    "id": name,
                    "category": self._nodes[name][0],
                    "payload": json.loads(self._nodes[name][1]),
                }
                for name in sorted(selected)
            ],
            "edges": [
                edge.record()
                for edge in self._edges
                if edge.source in selected and edge.target in selected
            ],
        }


def kind_fingerprint(records: Mapping[str, Any] | SemanticGraph, root: str) -> CanonicalIdentity:
    graph = records if isinstance(records, SemanticGraph) else SemanticGraph(records)
    return canonical_identity("kind", graph.rooted_record(root))


def definition_fingerprint(definition: Any) -> CanonicalIdentity:
    return canonical_identity("definition", definition)


def eligibility_fingerprint(eligibility: Any) -> CanonicalIdentity:
    return canonical_identity("eligibility", eligibility)


def validate_opaque_boundary(boundary: Mapping[str, Any]) -> None:
    """Require captured bytes or an immutable resolved contract, for every frontend."""
    for name in ("reference", "contract", "role"):
        _identifier(boundary.get(name), f"opaque boundary {name}")
    if not isinstance(boundary.get("reuse_eligible", True), bool):
        raise ValueError("opaque boundary reuse_eligible must be boolean")
    digest = boundary.get("content_digest")
    if digest is None:
        # Resolution/admission belongs to the effective-model owner. A mutable
        # contract name alone cannot stand in for its immutable resolved revision.
        if not re.fullmatch(r"contract:[0-9a-f]{64}", boundary["contract"]):
            raise ValueError(
                "opaque boundary requires captured content or resolved contract revision"
            )
    elif not isinstance(digest, str) or not re.fullmatch(r"(?:sha256:)?[0-9a-f]{64}", digest):
        raise ValueError("opaque boundary content_digest must be a SHA-256 digest")


def implementation_slice_fingerprint(
    records: Mapping[str, Any], root: str, *, unknowns: Iterable[Mapping[str, Any]] | None = None
) -> CanonicalIdentity:
    if unknowns is None:
        if "unknowns" not in records:
            raise ValueError("implementation slice requires explicit dependency coverage")
        unknowns = records["unknowns"]
    required_unknowns = [row for row in unknowns if row.get("required", True)]
    if required_unknowns:
        raise ValueError(f"unknown required implementation dependencies: {required_unknowns!r}")
    normalization = _identifier(records.get("normalization"), "slice normalization contract")
    boundaries = list(records.get("boundaries", ()))
    for boundary in boundaries:
        validate_opaque_boundary(boundary)
    boundaries.sort(key=lambda item: canonical_bytes(semantic_value(item)))
    return canonical_identity(
        "implementation-slice",
        {
            "graph": SemanticGraph(records).rooted_record(root),
            "normalization": normalization,
            "boundaries": boundaries,
        },
    )


def recipe_fingerprint(
    recipe: Any, *, implementation_slices: Iterable[CanonicalIdentity] = ()
) -> CanonicalIdentity:
    slices = []
    for identity in implementation_slices:
        if identity.domain != "implementation-slice":
            raise ValueError("recipe implementation determinant must be an admitted slice identity")
        slices.append(identity.key)
    return canonical_identity(
        "recipe", {"recipe": recipe, "implementation_slices": sorted(set(slices))}
    )


def body_identity(body: Any) -> CanonicalIdentity:
    return canonical_identity("body", body)


@dataclass(frozen=True)
class ProfileField:
    name: str
    value: Any
    role: Literal["semantic", "execution"]


@dataclass(frozen=True)
class ProfileIdentities:
    inference: CanonicalIdentity
    execution: CanonicalIdentity


def profile_identities(fields: Iterable[ProfileField]) -> ProfileIdentities:
    """Field-owned roles determine projections, never an exclusion list of names."""
    semantic = []
    execution = []
    names = set()
    for item in fields:
        _identifier(item.name, "profile field")
        if item.name in names:
            raise ValueError(f"duplicate profile field {item.name!r}")
        names.add(item.name)
        if item.role not in {"semantic", "execution"}:
            raise ValueError(f"profile field {item.name!r} has no admitted role")
        execution.append((item.name, {"role": item.role, "value": item.value}))
        if item.role == "semantic":
            semantic.append((item.name, item.value))
    return ProfileIdentities(
        canonical_identity("inference", semantic_fields(semantic)),
        canonical_identity("execution-profile", semantic_fields(execution)),
    )


def contextual_product_identity(
    *, kind: str, context: SubjectContext, body: str
) -> CanonicalIdentity:
    """Complete contextual identity used by current native publication."""
    return canonical_identity(
        "product",
        {
            "kind": _identifier(kind, "kind fingerprint"),
            "subject": context.subject,
            "subject_context": context.identity_record,
            "body": _identifier(body, "body digest"),
        },
    )


def runtime_artifact_identity(executable_inputs: Any) -> CanonicalIdentity:
    """Only executable inputs; release binding belongs in the attestation."""
    return canonical_identity("runtime-artifact", executable_inputs)


def execution_attestation(
    *, runtime_artifact: str, release: str, execution_profile: str, observed: Any
) -> CanonicalIdentity:
    return canonical_identity(
        "execution-attestation",
        {
            "runtime_artifact": runtime_artifact,
            "release": release,
            "execution_profile": execution_profile,
            "observed": observed,
        },
    )


def _owned_value(value: Any) -> Any:
    """Own immutable semantic inputs so exposed fields agree with their identity bytes."""
    if isinstance(value, Mapping):
        return MappingProxyType({key: _owned_value(item) for key, item in value.items()})
    if isinstance(value, (list, tuple)):
        return tuple(_owned_value(item) for item in value)
    if isinstance(value, CollectionValue):
        return CollectionValue(value.kind, tuple(_owned_value(item) for item in value.members))
    if isinstance(value, OptionalValue):
        return OptionalValue(value.state, _owned_value(value.value))
    return value


@dataclass(frozen=True)
class SemanticRequestKey:
    recipe: str
    subject: str
    inputs: Any
    parameters: Any
    inference: str
    subject_context: SubjectContext = field(kw_only=True)
    execution_scope: str | None = field(default=None, kw_only=True)
    identity: CanonicalIdentity = field(init=False)

    def __post_init__(self) -> None:
        if self.subject_context.subject != self.subject:
            raise ValueError("request subject differs from complete context")
        object.__setattr__(self, "inputs", _owned_value(self.inputs))
        object.__setattr__(self, "parameters", _owned_value(self.parameters))
        object.__setattr__(
            self,
            "identity",
            canonical_identity(
                "semantic-request",
                {
                    "recipe": _identifier(self.recipe, "request recipe"),
                    "subject": _identifier(self.subject, "request subject"),
                    "subject_context": self.subject_context.identity_record,
                    "inputs": self.inputs,
                    "parameters": self.parameters,
                    "inference": _identifier(self.inference, "request inference policy"),
                    **(
                        {"execution_scope": _identifier(self.execution_scope, "execution scope")}
                        if self.execution_scope is not None
                        else {}
                    ),
                },
            ),
        )


@dataclass(frozen=True)
class AdmissionManifest:
    request_key: str
    binding_revision: str
    selected_support: Any
    authorization: Any
    execution_profile: str
    identity: CanonicalIdentity = field(init=False)

    def __post_init__(self) -> None:
        object.__setattr__(self, "selected_support", _owned_value(self.selected_support))
        object.__setattr__(self, "authorization", _owned_value(self.authorization))
        object.__setattr__(
            self,
            "identity",
            canonical_identity(
                "admission-manifest",
                {
                    "request_key": _identifier(self.request_key, "admission request key"),
                    "binding_revision": _identifier(self.binding_revision, "binding revision"),
                    "selected_support": self.selected_support,
                    "authorization": self.authorization,
                    "execution_profile": _identifier(self.execution_profile, "execution profile"),
                },
            ),
        )
