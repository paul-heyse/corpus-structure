"""Frozen native Demand intent and bounded relational request planning.

This is a semantic frontier. Physical supervision and provider scheduling consume
its ready requests; they never supply missing semantic inputs or success fates.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from hashlib import sha256
from typing import TYPE_CHECKING, Any, Literal

import networkx as nx
from pydantic import TypeAdapter

from .data_operation_compilation import project_operation_binding
from .data_operation_json import json_bytes, json_loads, wire_json_loads
from .data_operation_model import (
    EffectiveDataOperationModel,
    ResolvedOperationBinding,
    SubjectContext,
    json_context_meaning,
)
from .data_operation_source_sets import FrozenSourceSet, read_source_sets, source_sets_record
from .data_operation_support import (
    OriginalSourceSelection,
    original_source_selections_record,
    support_reference_records,
)
from .identity import canonical_bytes

if TYPE_CHECKING:
    from .data_operation_bindings import BindingResult
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
        return wire_json_loads(self.content)


def freeze_demand(
    model: EffectiveDataOperationModel,
    *,
    roots: tuple[RootSubject, ...],
    targets: tuple[str, ...],
    selections: tuple[OperationSelection, ...] = (),
    discovery: tuple[DiscoverySelection, ...] = (),
    inference: str,
    execution_profile: str,
    source_sets: tuple[FrozenSourceSet, ...] = (),
    original_sources: tuple[OriginalSourceSelection, ...] = (),
) -> DemandIntent:
    """Freeze the selected closure, not the union of every possible producer."""
    from .data_operation_bindings import effective_binding_parameters
    from .data_operation_identity import decode_semantic_value, semantic_value

    if not targets or not inference or not execution_profile:
        raise ValueError("demand requires targets, inference and an execution profile")
    if len(
        {
            (root.subject, root.original_source, json_context_meaning(root.analyzed_scope))
            for root in roots
        }
    ) != len(roots):
        raise ValueError("duplicate root context")
    if any(not root.subject or not root.original_source for root in roots):
        raise ValueError("root subject and source must be explicit")
    frozen_source_sets = source_sets_record(source_sets)
    frozen_original_sources = original_source_selections_record(original_sources)
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
    if not nx.is_directed_acyclic_graph(graph, backend="networkx"):
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
        closure.update(nx.descendants(graph, target, backend="networkx"))
    root_operations = set(targets) | {relation.producer for relation in discovery}
    for target in tuple(root_operations):
        root_operations.update(nx.descendants(graph, target, backend="networkx"))
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
        required_source_sets = {
            role.support.source_set
            for role in operation.roles
            if role.support is not None and role.support.source_set is not None
        }
        if not required_source_sets <= frozen_source_sets.keys():
            raise ValueError("selected operation lacks its explicit frozen source set")
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
    declared_source_sets = {
        role.support.source_set
        for operation_id in closure
        for role in operations[operation_id].roles
        if role.support is not None and role.support.source_set is not None
    }
    if frozen_source_sets.keys() != declared_source_sets:
        raise ValueError("frozen source sets must exactly match selected operation declarations")
    return DemandIntent(
        json_bytes(
            {
                "version": "data-demand-intent-v1",
                "model": sha256(model.content).hexdigest(),
                "roots": sorted(
                    (
                        {
                            "subject": root.subject,
                            "original_source": root.original_source,
                            "analyzed_scope": json_loads(root.analyzed_scope),
                        }
                        for root in roots
                    ),
                    key=lambda root: (
                        root["subject"],
                        root["original_source"],
                        json_bytes(root["analyzed_scope"]),
                    ),
                ),
                "targets": sorted(set(targets)),
                "operations": selected,
                "root_operations": sorted(root_operations),
                **({"source_sets": frozen_source_sets} if frozen_source_sets else {}),
                **(
                    {"original_sources": frozen_original_sources} if frozen_original_sources else {}
                ),
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
    binding: bytes
    resolved: ResolvedOperationBinding
    binding_result: BindingResult

    def __post_init__(self) -> None:
        if not self.binding_result.sufficient or (
            self.binding_result.operation,
            self.binding_result.subject,
            self.binding_result.roles,
            self.binding_result.parameters,
        ) != (
            self.resolved.operation,
            self.resolved.subject,
            self.resolved.roles,
            self.resolved.parameters,
        ):
            raise ValueError("ready request must retain its sufficient original binding")
        disposition = json.loads(self.native)
        action = disposition.get("action")
        retained = disposition.get("retained_intent_id")
        if action not in {"compute", "reconcile"}:
            raise ValueError("executable request requires a native compute/reconcile disposition")
        if (action == "reconcile") != (isinstance(retained, str) and bool(retained)):
            raise ValueError("native reconciliation requires the exact retained intent")
        if action == "compute" and retained is not None:
            raise ValueError("compute cannot discard a retained intent")

    @property
    def action(self) -> Literal["compute", "reconcile"]:
        """The native owner decides whether inference or exact reconciliation is next."""
        return json.loads(self.native)["action"]

    @property
    def retained_intent_id(self) -> str | None:
        return json.loads(self.native).get("retained_intent_id")


def _population_context_matches(
    row: dict, obligation: dict, *, source_set: str | None, source_sets: dict, project: str
) -> bool:
    """Use authenticated contexts, or an explicitly frozen exact member association."""

    def same_context(left: dict, right: dict) -> bool:
        return all(left.get(key) == right[key] for key in ("subject", "original_source")) and (
            json_context_meaning(json_bytes(left.get("analyzed_scope")))
            == json_context_meaning(json_bytes(right["analyzed_scope"]))
        )

    evidence = row["evidence"]
    selected = evidence.get("selection")
    if selected is not None:
        return (
            selected.get("obligation_id") == obligation["obligation_id"]
            and selected.get("operation_id") == obligation["operation_id"]
            and same_context(selected, obligation)
        )
    producer = evidence.get("producer_context")
    if producer is None:
        return False
    if same_context(producer, obligation):
        return True
    if source_set is None:
        return False
    members = {member["member_id"]: member for member in row["members"]}
    return any(
        entry["project_id"] == project
        and entry["product"] == evidence["product_id"]
        and entry["original_source"] == producer.get("original_source")
        and entry["member"] in members
        and same_context(entry, members[entry["member"]])
        for entry in source_sets.get(source_set, ())
    )


class DemandPlanner:
    """Advance a native Demand from compiled SQL bindings in bounded batches."""

    def __init__(self, model: EffectiveDataOperationModel, storage: DataOperationStorage):
        self.model = model
        self.storage = storage
        self.selected_population_ids: tuple[str, ...] = ()
        self.fulfilled_request_ids: tuple[str, ...] = ()

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
        if result.get("state") == "cancelled":
            return result
        for name, source in record.get("original_sources", {}).items():
            self.storage.invoke(
                (
                    "admit_original_document_asset"
                    if source["reference"].get("kind") == "original-document"
                    else "admit_original_source_view"
                ),
                {
                    "demand_id": result["demand_id"],
                    "selection_name": name,
                    **source,
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
        read_id: str | None = None,
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
        if read_id is not None:
            request["read_id"] = read_id
        snapshot = self.storage.invoke("read_demand_result", request)
        frozen = snapshot["intent"]
        if frozen["model"] != sha256(self.model.content).hexdigest():
            raise ValueError("resume requires the demand's original effective model")
        # Inspect uncertain completions before returning any executable work.
        inspections = {}
        for obligation in snapshot["obligations"]:
            if obligation.get("intent_id") is not None:
                inspections[obligation["intent_id"]] = self.storage.invoke(
                    "inspect_data_completion",
                    {
                        "intent_id": obligation["intent_id"],
                        "demand_id": demand,
                        "request_id": obligation["request_id"],
                        "generation": obligation["generation"],
                    },
                )
        # These are current receipt observations, distinct from the pinned frontier.
        # Returning them lets the execution owner settle uncertainty without inference.
        return {**snapshot, "completion_inspections": inspections}

    def ready(self, snapshot: dict, *, authorization: bytes) -> tuple[ReadyDataRequest, ...]:
        self.selected_population_ids = ()
        self.fulfilled_request_ids = ()
        if snapshot.get("state") == "cancelled":
            return ()

        from .data_operation_bindings import (
            BindingReason,
            PopulationBinding,
            compile_binding,
            execute_binding,
        )
        from .data_operation_identity import decode_semantic_value, semantic_value
        from .data_operation_storage import admitted_data_projection

        if snapshot.get("state") == "cancelled":
            return ()

        frozen = snapshot["intent"]
        if frozen["model"] != sha256(self.model.content).hexdigest():
            raise ValueError("binding requires the demand's retained model")
        selected = {item["operation"]: item for item in frozen["operations"]}
        source_sets = frozen.get("source_sets", {})
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
                read_id=snapshot["read_id"],
                subject=obligation["subject"],
                original_source=obligation["original_source"],
                analyzed_scope=obligation["analyzed_scope"],
            )
            binding_arguments = dict(
                subject_context=SubjectContext(
                    snapshot["project_id"],
                    obligation["subject"],
                    obligation["original_source"],
                    json_bytes(obligation["analyzed_scope"]),
                ),
                subject=obligation["subject"],
                parameters=decode_semantic_value(operation["parameter_meaning"]),
                choices=operation["choices"],
                source_sets=read_source_sets(source_sets),
                original_source=obligation["original_source"],
            )
            # Compile once without witnesses to obtain the shared AST's active
            # role/population associations, including its frozen branch choices.
            compiled = compile_binding(
                self.model,
                operation["operation"],
                projections,
                **binding_arguments,
            )
            prerequisites, pending = set(), list(operation["dependencies"])
            while pending:
                prerequisite = pending.pop()
                if prerequisite not in prerequisites:
                    prerequisites.add(prerequisite)
                    pending.extend(selected[prerequisite]["dependencies"])
            operation_roles = {
                role.name: role
                for role in self.model.operation(operation["operation"]).roles
                if role.direction == "input"
            }
            population_rows, ambiguities, derived = {}, [], False
            for role_name, population_name in compiled.population_roles:
                role = operation_roles[role_name]
                scope_name = role.support.source_set if role.support is not None else None
                contextual = [
                    row
                    for row in snapshot["populations"]
                    if _population_context_matches(
                        row,
                        obligation,
                        source_set=scope_name,
                        source_sets=source_sets,
                        project=snapshot["project_id"],
                    )
                ]
                parents = []
                for row in contextual:
                    if "selection" in row["evidence"]:
                        continue
                    producer = row["evidence"]["producer_context"]["operation_id"]
                    if producer not in prerequisites:
                        continue
                    relations = [
                        relation
                        for relation in frozen["discovery"]
                        if relation["producer"] == producer
                        and relation["population"] == row["name"]
                        and relation["output_role"] == row["evidence"]["member_role"]
                    ]
                    if not relations:
                        continue
                    from .data_operation_kind_refinements import input_kind_refinements
                    from .data_operation_member_contracts import derive_member_kinds

                    outputs = [
                        output
                        for output in self.model.operation(producer).roles
                        if output.direction == "output"
                        and output.name == row["evidence"]["member_role"]
                    ]
                    if len(outputs) == 1 and set(
                        input_kind_refinements(self.model, (role.kind,))[role.kind]
                    ).intersection(derive_member_kinds(self.model, outputs[0].kind)):
                        parents.append(row)
                existing = [
                    row
                    for row in contextual
                    if row["name"] == population_name and "selection" in row["evidence"]
                ]
                existing.extend(row for row in parents if row["name"] == population_name)
                if len(existing) > 1:
                    ambiguities.append(role_name)
                    continue
                if existing:
                    population_rows[population_name] = existing[0]
                    continue
                if len(parents) > 1:
                    query = dict(compiled.queries).get(role_name)
                    if query is not None:
                        qualified = {
                            (value["product"], value["member"])
                            for value in self.storage.connection.execute(query).mappings()
                        }
                        positive = [
                            row
                            for row in parents
                            if any(
                                (row["evidence"]["product_id"], member["member_id"]) in qualified
                                for member in row["members"]
                            )
                        ]
                        if len(positive) == 1:
                            parents = positive
                if len(parents) > 1:
                    ambiguities.append(role_name)
                elif parents:
                    receipt = self.storage.invoke(
                        "select_data_population",
                        {
                            "obligation_id": obligation["obligation_id"],
                            "population_name": population_name,
                            "parent_population_id": parents[0]["population_id"],
                            "read_id": snapshot["read_id"],
                        },
                    )
                    self.selected_population_ids += (receipt["population_id"],)
                    derived = True
            if ambiguities:
                self.storage.invoke(
                    "record_data_fate",
                    {
                        "obligation_id": obligation["obligation_id"],
                        "fate": "awaiting-population",
                        "selection": {
                            "reasons": [
                                asdict(
                                    BindingReason(
                                        "ambiguous-population",
                                        operation["operation"] + "/" + role_name,
                                        (
                                            "more than one authenticated population "
                                            "fits the declared role"
                                        ),
                                    )
                                )
                                for role_name in ambiguities
                            ]
                        },
                    },
                )
                continue
            if derived:
                # Receipt writes belong to a new read boundary. The execution
                # owner observes this progress and resumes before attaching work.
                continue
            populations = tuple(
                PopulationBinding(
                    row["name"],
                    row["semantic_key"],
                    row["complete"],
                    tuple(member["member_id"] for member in row["members"]),
                    json_bytes(
                        {
                            **row["evidence"],
                            "population_id": row["population_id"],
                            "name": row["name"],
                        }
                    ),
                )
                for row in population_rows.values()
            )
            compiled = compile_binding(
                self.model,
                operation["operation"],
                projections,
                populations=populations,
                **binding_arguments,
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
                subject_context=SubjectContext(
                    snapshot["project_id"],
                    obligation["subject"],
                    obligation["original_source"],
                    json_bytes(obligation["analyzed_scope"]),
                ),
                inference=frozen["inference"],
                authorization=authorization,
                trust_evidence=json_bytes(
                    {
                        "demand_id": snapshot["demand_id"],
                        "obligation_id": obligation["obligation_id"],
                        "original_source": obligation["original_source"],
                        "analyzed_scope": obligation["analyzed_scope"],
                        "trust": snapshot["trust_snapshot"],
                        "read_id": snapshot["read_id"],
                        "read_snapshot": snapshot["read_snapshot"],
                        "frontier_at": snapshot["frontier_at"],
                    }
                ),
                execution_profile=frozen["execution_profile"],
                replicate=operation["replicate"],
            )
            request, admission = project_operation_binding(self.model, resolved)
            inputs, support, population_refs = [], [], []
            for role in resolved.roles:
                if role.population_witness is not None:
                    witness = json.loads(role.population_witness)
                    evidence = witness.get("evidence")
                    if evidence is not None:
                        population_refs.append(
                            {
                                "role": role.role,
                                "name": evidence["name"],
                                "population_id": evidence["population_id"],
                            }
                        )
                        support.append(
                            {
                                "derivation_id": evidence["derivation_id"],
                                "role": "population:" + evidence["name"],
                                "position": 0,
                                "admission_use_id": evidence["admission_use_id"],
                            }
                        )
                for member in role.members:
                    for reference in support_reference_records(member.support_references):
                        support.append(
                            {**reference, "role": role.role, "position": member.position}
                        )
                    inputs.append(
                        {
                            "role": role.role,
                            "position": member.position,
                            "multiplicity": member.multiplicity,
                            "product_id": member.product,
                            "member_id": member.member,
                            **(
                                {"support_derivation_id": member.support_episodes[0]}
                                if member.support_episodes
                                else {}
                            ),
                        }
                    )
            wire_binding = {
                "inputs": inputs,
                "support": support,
                "populations": population_refs,
                "parameters": semantic_value(request.parameters),
                "request_inputs": semantic_value(request.inputs),
                "inference": frozen["inference"],
                "read_id": snapshot["read_id"],
            }
            # The pinned native view names a directly trusted historical producer.
            # The hint is not authority: attachment revalidates it under trust locks.
            rebind = next(
                (
                    use["rebind_derivation"]
                    for use in snapshot.get("uses", ())
                    if use.get("obligation_id") == obligation["obligation_id"]
                    and use.get("request_id") == request.identity.key
                    and use.get("rebind_derivation")
                ),
                None,
            )
            native = self.storage.invoke(
                "attach_data_request",
                {
                    **({"rebind_derivation": rebind} if rebind is not None else {}),
                    "obligation_id": obligation["obligation_id"],
                    "request_meaning": json.loads(request.identity.canonical_input),
                    "request_key": request.identity.key,
                    "binding": wire_binding,
                    "replicate": operation["replicate"],
                },
            )
            if native["fate"] == "fulfilled":
                self.fulfilled_request_ids += (native["request_id"],)
                continue
            ready.append(
                ReadyDataRequest(
                    obligation["obligation_id"],
                    operation["operation"],
                    obligation["subject"],
                    request.identity.canonical_input,
                    admission.identity.canonical_input,
                    canonical_bytes(native),
                    canonical_bytes(wire_binding),
                    resolved,
                    binding,
                )
            )
        return tuple(ready)
