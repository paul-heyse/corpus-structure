"""Frozen native Demand intent and bounded relational request planning.

This is a semantic frontier. Physical supervision and provider scheduling consume
its ready requests; they never supply missing semantic inputs or success fates.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from hashlib import sha256
from typing import TYPE_CHECKING, Any

import networkx as nx
from pydantic import TypeAdapter

from .data_operation_compilation import project_operation_binding
from .data_operation_model import EffectiveDataOperationModel
from .identity import canonical_bytes

if TYPE_CHECKING:
    from .data_operation_storage import DataOperationStorage


@dataclass(frozen=True)
class RootSubject:
    subject: str
    original_source: str
    analyzed_scope: bytes


@dataclass(frozen=True)
class OperationSelection:
    operation: str
    parameters: bytes = b"{}"
    choices: bytes = b"{}"
    selected_dependencies: tuple[str, ...] = ()
    replicate: str | None = None
    parameter_meaning: bytes | None = None


@dataclass(frozen=True)
class DiscoverySelection:
    producer: str
    output_role: str
    target: str
    population: str


@dataclass(frozen=True)
class DemandIntent:
    """Captured meaning, with no references to mutable defaults or a live query."""

    content: bytes

    @property
    def record(self) -> dict[str, Any]:
        return json.loads(self.content)


def freeze_demand(
    model: EffectiveDataOperationModel,
    *,
    roots: tuple[RootSubject, ...],
    targets: tuple[str, ...],
    selections: tuple[OperationSelection, ...] = (),
    discovery: tuple[DiscoverySelection, ...] = (),
    inference: str,
    execution_profile: str,
) -> DemandIntent:
    """Freeze the selected closure, not the union of every possible producer."""
    from .data_operation_bindings import effective_binding_parameters
    from .data_operation_identity import decode_semantic_value, semantic_value

    if not targets or not inference or not execution_profile:
        raise ValueError("demand requires targets, inference and an execution profile")
    if len({root.subject for root in roots}) != len(roots):
        raise ValueError("duplicate root subject")
    if any(not root.subject or not root.original_source for root in roots):
        raise ValueError("root subject and source must be explicit")
    supplied = {item.operation: item for item in selections}
    if len(supplied) != len(selections):
        raise ValueError("duplicate operation selection")
    operations = {op.semantic_id: op for op in model.operations}
    graph = nx.DiGraph()
    graph.add_nodes_from(operations)
    for operation in model.operations:
        selection = supplied.get(operation.semantic_id, OperationSelection(operation.semantic_id))
        potential = set(operation.potential_dependencies)
        if not set(selection.selected_dependencies) <= potential:
            raise ValueError("selected dependency is outside the declared alternatives")
        graph.add_edges_from(
            (operation.semantic_id, dependency)
            for dependency in (*operation.dependencies, *selection.selected_dependencies)
        )
    if not nx.is_directed_acyclic_graph(graph):
        raise ValueError("selected demand dependency cycle")
    requested = set(targets)
    for relation in discovery:
        producer = operations.get(relation.producer)
        if (
            producer is None
            or producer.profile != "discovery"
            or relation.target not in operations
            or not relation.population
            or not any(
                role.name == relation.output_role and role.direction == "output"
                for role in producer.roles
            )
        ):
            raise ValueError("discovery relation is outside declared output contracts")
        requested.update((relation.producer, relation.target))
    if not requested <= operations.keys():
        raise ValueError("unknown demand target")
    closure = set(requested)
    for target in requested:
        closure.update(nx.descendants(graph, target))
    root_operations = set(targets) | {relation.producer for relation in discovery}
    for target in tuple(root_operations):
        root_operations.update(nx.descendants(graph, target))
    if not supplied.keys() <= closure:
        raise ValueError("selection is outside the requested closure")
    identities = {(item.owner, item.domain): item.key for item in model.identities}
    selected = []
    for operation_id in sorted(closure):
        operation = operations[operation_id]
        item = supplied.get(operation_id, OperationSelection(operation_id))
        if (operation_id, "recipe") not in identities:
            raise ValueError(f"unknown implementation determinants: {operation_id}")
        if operation.replicate_policy == "explicit-replicates":
            if not item.replicate:
                raise ValueError("explicit replicate selection is required")
        elif item.replicate is not None:
            raise ValueError("deterministic operation cannot select a replicate")
        parameters, choices = json.loads(item.parameters), json.loads(item.choices)
        if item.parameter_meaning is not None:
            parameters = decode_semantic_value(json.loads(item.parameter_meaning))
        if not isinstance(parameters, dict) or not isinstance(choices, dict):
            raise ValueError("operation parameters and choices must be mappings")
        parameters = effective_binding_parameters(operation, parameters)
        selected.append(
            {
                "operation": operation_id,
                "parameters": TypeAdapter(dict[str, Any]).dump_python(parameters, mode="json"),
                "parameter_meaning": semantic_value(parameters),
                "choices": choices,
                "replicate": item.replicate,
                "dependencies": sorted(graph.successors(operation_id)),
                "definition": identities[operation_id, "definition"],
                "recipe": identities[operation_id, "recipe"],
                "eligibility": identities[operation_id, "eligibility"],
            }
        )
    return DemandIntent(
        canonical_bytes(
            {
                "version": "data-demand-intent-v1",
                "model": sha256(model.content).hexdigest(),
                "roots": sorted(
                    (
                        {
                            "subject": root.subject,
                            "original_source": root.original_source,
                            "analyzed_scope": json.loads(root.analyzed_scope),
                        }
                        for root in roots
                    ),
                    key=lambda root: root["subject"],
                ),
                "targets": sorted(set(targets)),
                "operations": selected,
                "root_operations": sorted(root_operations),
                "discovery": [asdict(item) for item in discovery],
                "inference": inference,
                "execution_profile": execution_profile,
            }
        )
    )


@dataclass(frozen=True)
class ReadyDataRequest:
    obligation: str
    operation: str
    subject: str
    request: bytes
    admission: bytes
    native: bytes


class DemandPlanner:
    """Advance a native Demand from compiled SQL bindings in bounded batches."""

    def __init__(self, model: EffectiveDataOperationModel, storage: DataOperationStorage):
        self.model = model
        self.storage = storage

    def register(
        self,
        intent: DemandIntent,
        *,
        project: str,
        release: str,
        runtime: str,
        strength: str = "value",
    ) -> dict:
        record = intent.record
        if record["model"] != sha256(self.model.content).hexdigest():
            raise ValueError("demand intent belongs to a different effective model")
        result = self.storage.invoke(
            "register_data_demand",
            {
                "project_id": project,
                "release_id": release,
                "runtime_id": runtime,
                "root": record["roots"],
                "selection": record,
                "strength": strength,
            },
        )
        for root in record["roots"]:
            for operation in record["operations"]:
                if operation["operation"] not in record["root_operations"]:
                    continue
                self.storage.invoke(
                    "expand_data_obligation",
                    {
                        "demand_id": result["demand_id"],
                        "operation_id": operation["operation"],
                        **root,
                        "parameters": operation["parameters"],
                    },
                )
        return result

    def expand_discovery(
        self, snapshot: dict, *, population: str, product: str, derivation: str
    ) -> dict:
        """Expand only native-authenticated members of a declared discovery output."""
        frozen = snapshot["intent"]
        relations = [item for item in frozen["discovery"] if item["population"] == population]
        if len(relations) != 1:
            raise ValueError("discovery population is not uniquely selected by this demand")
        relation = relations[0]
        closed = self.storage.invoke(
            "close_data_population",
            {
                "demand_id": snapshot["demand_id"],
                "name": population,
                "product_id": product,
                "derivation_id": derivation,
                "member_role": relation["output_role"],
            },
        )
        selected = {item["operation"]: item for item in frozen["operations"]}
        closure, pending = set(), [relation["target"]]
        while pending:
            operation = pending.pop()
            if operation not in closure:
                closure.add(operation)
                pending.extend(selected[operation]["dependencies"])
        # Partial positive discovery can expose members. Only the native complete
        # witness can prove absence or closed fan-in on a subsequent binding.
        for member in closed["members"]:
            for operation in sorted(closure):
                self.storage.invoke(
                    "expand_data_obligation",
                    {
                        "demand_id": snapshot["demand_id"],
                        "operation_id": operation,
                        "subject": member["subject"],
                        "original_source": member["original_source"],
                        "analyzed_scope": member["analyzed_scope"],
                        "parameters": selected[operation]["parameters"],
                        "population_id": closed["population_id"],
                    },
                )
        return closed

    def resume(
        self,
        demand: str,
        selection: dict | None = None,
        *,
        limit: int = 100,
        after: str | None = None,
        trust_snapshot: dict | None = None,
    ) -> dict:
        if type(limit) is not int or not 1 <= limit <= 1000:
            raise ValueError("demand frontier limit must be between one and 1000")
        request: dict[str, Any] = {"demand_id": demand, "limit": limit}
        if selection is not None:
            request["selection"] = selection
        if after is not None:
            request["after"] = after
        if trust_snapshot is not None:
            request["trust_snapshot"] = trust_snapshot
        snapshot = self.storage.invoke("read_demand_result", request)
        frozen = snapshot["intent"]
        if frozen["model"] != sha256(self.model.content).hexdigest():
            raise ValueError("resume requires the demand's original effective model")
        # Inspect uncertain completions before returning any executable work.
        for obligation in snapshot["obligations"]:
            if obligation.get("intent_id") is not None:
                self.storage.invoke(
                    "inspect_data_completion",
                    {
                        "intent_id": obligation["intent_id"],
                        "demand_id": demand,
                    },
                )
        return snapshot

    def ready(self, snapshot: dict, *, authorization: bytes) -> tuple[ReadyDataRequest, ...]:
        from .data_operation_bindings import PopulationBinding, compile_binding, execute_binding
        from .data_operation_identity import decode_semantic_value, semantic_value
        from .data_operation_storage import admitted_data_projection

        frozen = snapshot["intent"]
        if frozen["model"] != sha256(self.model.content).hexdigest():
            raise ValueError("binding requires the demand's retained model")
        selected = {item["operation"]: item for item in frozen["operations"]}
        populations = tuple(
            PopulationBinding(
                row["name"],
                row["population_id"],
                row["complete"],
                tuple(
                    member["member_id"] if isinstance(member, dict) else member
                    for member in row["members"]
                ),
                canonical_bytes(row["evidence"]),
            )
            for row in snapshot["populations"]
        )
        ready = []
        for obligation in snapshot["obligations"]:
            if obligation["fate"] in {"fulfilled", "closed", "cancelled", "failed"}:
                continue
            operation = selected[obligation["operation_id"]]
            projections = admitted_data_projection(
                self.storage.connection,
                snapshot["demand_id"],
                operation["operation"],
                snapshot["trust_snapshot"],
                self.model,
            )
            compiled = compile_binding(
                self.model,
                operation["operation"],
                projections,
                subject=obligation["subject"],
                parameters=decode_semantic_value(operation["parameter_meaning"]),
                choices=operation["choices"],
                populations=populations,
            )
            binding = execute_binding(self.storage.connection, compiled)
            if not binding.sufficient:
                self.storage.invoke(
                    "record_data_fate",
                    {
                        "obligation_id": obligation["obligation_id"],
                        "fate": binding.status,
                        "selection": {"reasons": [asdict(reason) for reason in binding.reasons]},
                    },
                )
                continue
            resolved = binding.resolved(
                inference=frozen["inference"],
                authorization=authorization,
                trust_evidence=canonical_bytes(snapshot["trust_snapshot"]),
                execution_profile=frozen["execution_profile"],
                replicate=operation["replicate"],
            )
            request, admission = project_operation_binding(self.model, resolved)
            inputs, support = [], []
            for role in resolved.roles:
                for member in role.members:
                    for episode in member.support_episodes:
                        evidence = json.loads(member.support_evidence)
                        support.append(
                            {
                                "derivation_id": episode,
                                "role": role.role,
                                "position": member.position,
                                **(
                                    {"admission_use_id": evidence["use_id"]}
                                    if evidence.get("use_id") is not None
                                    else {}
                                ),
                            }
                        )
                    inputs.append(
                        {
                            "role": role.role,
                            "position": member.position,
                            "multiplicity": member.multiplicity,
                            "product_id": member.product,
                            "member_id": member.member,
                            "support_derivation_id": (
                                member.support_episodes[0] if member.support_episodes else None
                            ),
                        }
                    )
            native = self.storage.invoke(
                "attach_data_request",
                {
                    "obligation_id": obligation["obligation_id"],
                    "request_meaning": json.loads(request.identity.canonical_input),
                    "request_key": request.identity.key,
                    "binding": {
                        "inputs": inputs,
                        "support": support,
                        "parameters": semantic_value(request.parameters),
                        "request_inputs": semantic_value(request.inputs),
                        "inference": frozen["inference"],
                    },
                    "replicate": operation["replicate"],
                },
            )
            ready.append(
                ReadyDataRequest(
                    obligation["obligation_id"],
                    operation["operation"],
                    obligation["subject"],
                    request.identity.canonical_input,
                    admission.identity.canonical_input,
                    canonical_bytes(native),
                )
            )
        return tuple(ready)
