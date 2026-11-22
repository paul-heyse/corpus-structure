"""Frozen native Demand intent and bounded relational request planning.

This is a semantic frontier. Physical supervision and provider scheduling consume
its ready requests; they never supply missing semantic inputs or success fates.
"""

from __future__ import annotations

import json
from collections.abc import Mapping
from dataclasses import asdict, dataclass
from hashlib import sha256
from typing import TYPE_CHECKING, Any, Literal, TypedDict, cast

from pydantic import TypeAdapter
from sqlalchemy import Text, bindparam, func, select
from sqlalchemy.dialects.postgresql import ARRAY, JSONB

from corpus_structure.semantic._data_operation_wire import (
    WireAdmitAuthoredDataRequest,
    WireAdmitOriginalDocumentAssetRequest,
    WireAttachDataRequestsItem,
    WireAttachDataRequestsRequest,
    WireDemandId,
    WireDemandIntent,
    WireInspectDataCompletionRequest,
    WireInspectDataCompletionResult,
    WireObligationId,
    WireReadDemandResultRequest,
    WireReadDemandResultResult,
    WireReadIdentity,
    WireRecordDataFateRequest,
    WireRegisterDataDemandResult,
    WireSelectDataPopulationRequest,
)
from corpus_structure.semantic.identifiers import ProjectId, RuntimeId

from .data_operation_compilation import project_operation_binding
from .data_operation_json import json_bytes, json_loads, native_json_loads
from .data_operation_model import (
    EffectiveDataOperationModel,
    ResolvedOperationBinding,
    SubjectContext,
    json_context_meaning,
    validate_subject_source,
)
from .data_operation_source_sets import FrozenSourceSet, read_source_sets, source_sets_record
from .data_operation_support import (
    OriginalSourceSelection,
    original_source_selections_record,
    support_reference_records,
)
from .data_operation_wire import interpret_wire_record
from .graph_runtime import nx
from .graph_topology import rooted_closure
from .identifiers import ReleaseId
from .identity import canonical_bytes

if TYPE_CHECKING:
    from .data_operation_bindings import BindingResult
    from .data_operation_storage import DataOperationStorage


def _frozen_dependency_graph(selected, discovery=()):
    graph = nx.DiGraph(backend="networkx")
    graph.add_nodes_from(selected)
    edges = [
        (name, dependency)
        for name, operation in selected.items()
        for dependency in operation["dependencies"]
    ]
    edges.extend((relation["producer"], relation["target"]) for relation in discovery)
    if any(source not in selected or target not in selected for source, target in edges):
        raise ValueError("frozen dependency has an unknown operation")
    graph.add_edges_from(edges)
    return graph


@dataclass(frozen=True)
class RootSubject:
    subject: str
    original_source: str | None
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
    target_role: str | None = None


@dataclass(frozen=True)
class DemandIntent:
    """Captured meaning, with no references to mutable defaults or a live query."""

    content: bytes

    @property
    def record(self) -> WireDemandIntent:
        return cast(
            WireDemandIntent,
            interpret_wire_record("demand_intent", native_json_loads(self.content)),
        )


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
    from .data_operation_model import validate_replicate_selection
    from .data_operation_values import decode_semantic_value, semantic_value
    from .refusal_types import SemanticRefusal

    if not targets or not inference or not execution_profile:
        raise SemanticRefusal("demand requires targets, inference and an execution profile")
    if len(
        {
            (root.subject, root.original_source, json_context_meaning(root.analyzed_scope))
            for root in roots
        }
    ) != len(roots):
        raise SemanticRefusal("duplicate root context")
    if any(
        type(root.subject) is not str
        or not root.subject
        or (
            root.original_source is not None
            and (type(root.original_source) is not str or not root.original_source)
        )
        for root in roots
    ):
        raise SemanticRefusal("root subject and nullable source must be explicit")
    frozen_source_sets = source_sets_record(source_sets)
    for original in original_sources:
        original.validate_subject(model)
    frozen_original_sources = original_source_selections_record(original_sources)
    supplied = {item.operation: item for item in selections}
    if len(supplied) != len(selections):
        raise SemanticRefusal("duplicate operation selection")
    operations = {op.semantic_id: op for op in model.operations}
    graph = model.projection_graph(
        "selected-dependencies",
        selected_dependencies=tuple(
            (name, item.selected_dependencies) for name, item in supplied.items()
        ),
    )
    graph.require_acyclic({"operation_dependency", "selected_operation_dependency"})
    requested = set(targets)
    population_sources = {}
    seen_relations = set()
    for relation in discovery:
        source = (relation.producer, relation.output_role)
        if (
            relation.population in population_sources
            and population_sources[relation.population] != source
        ):
            raise SemanticRefusal("one discovery population requires one source projection")
        population_sources[relation.population] = source
        relation_key = (*source, relation.population, relation.target)
        if relation_key in seen_relations:
            raise SemanticRefusal("duplicate frozen discovery target")
        seen_relations.add(relation_key)
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
            raise SemanticRefusal("discovery relation is outside declared output contracts")
        if relation.target_role is not None:
            from .data_operation_kind_refinements import input_kind_refinements
            from .data_operation_member_contracts import derive_member_kinds

            target_roles = [
                role
                for role in operations[relation.target].roles
                if role.direction == "input" and role.name == relation.target_role
            ]
            output = next(
                role
                for role in producer.roles
                if role.direction == "output" and role.name == relation.output_role
            )
            if (
                len(target_roles) != 1
                or target_roles[0].support is None
                or "computation" not in target_roles[0].support.origins
            ):
                raise SemanticRefusal("discovery target role must accept computational members")
            target_role = target_roles[0]
            if not set(
                input_kind_refinements(model, (target_role.kind,))[target_role.kind]
            ).intersection(derive_member_kinds(model, output.kind)):
                raise SemanticRefusal(
                    "discovery target role does not accept the producer member kind"
                )
            if any(
                previous.target == relation.target and previous.target_role == relation.target_role
                for previous in discovery[: discovery.index(relation)]
            ):
                raise SemanticRefusal("discovery target role requires one frozen population")
        requested.update((relation.producer, relation.target))
    if not requested <= operations.keys():
        raise SemanticRefusal("unknown demand target")
    closure = set(requested)
    for target in requested:
        closure.update(graph.closure((target,)))
    root_operations = set(targets) | {relation.producer for relation in discovery}
    for target in tuple(root_operations):
        root_operations.update(graph.closure((target,)))
    # A selected fan-in dependency can run on discovered members while its
    # consumer runs on the document root. Do not also manufacture that child's
    # source-view obligation at the document's whole-document context. Explicit
    # top-level targets/producers retain their independently requested root work.
    member_operations = set()
    for relation in discovery:
        member_operations.add(relation.target)
        member_operations.update(graph.closure((relation.target,)))
    root_operations.difference_update(
        member_operations - set(targets) - {relation.producer for relation in discovery}
    )
    for operation_id in root_operations:
        for root in roots:
            validate_subject_source(model, operations[operation_id].subject, root.original_source)
    for source_set in source_sets:
        for entry in source_set.entries:
            validate_subject_source(model, entry.subject_definition, entry.original_source)
    if not supplied.keys() <= closure:
        raise SemanticRefusal("selection is outside the requested closure")
    identities = {(item.owner, item.domain): item.key for item in model.identities}
    selected = []
    for operation_id in sorted(closure):
        operation = operations[operation_id]
        item = supplied.get(operation_id, OperationSelection(operation_id))
        if (operation_id, "recipe") not in identities:
            raise SemanticRefusal(f"unknown implementation determinants: {operation_id}")
        validate_replicate_selection(operation.replicate_policy, item.replicate, owner=operation_id)
        parameters, choices = json.loads(item.parameters), json.loads(item.choices)
        if item.parameter_meaning is not None:
            parameters = decode_semantic_value(json.loads(item.parameter_meaning))
        if not isinstance(parameters, dict) or not isinstance(choices, dict):
            raise SemanticRefusal("operation parameters and choices must be mappings")
        parameters = effective_binding_parameters(operation, parameters)
        required_source_sets = {
            role.support.source_set
            for role in operation.roles
            if role.support is not None and role.support.source_set is not None
        }
        if not required_source_sets <= frozen_source_sets.keys():
            raise SemanticRefusal("selected operation lacks its explicit frozen source set")
        selected.append(
            {
                "operation": operation_id,
                "parameters": TypeAdapter(dict[str, Any]).dump_python(parameters, mode="json"),
                "parameter_meaning": semantic_value(parameters),
                "choices": choices,
                "replicate": item.replicate,
                "dependencies": list(graph.direct_dependencies(operation_id)),
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
        raise SemanticRefusal(
            "frozen source sets must exactly match selected operation declarations"
        )
    return DemandIntent(
        json_bytes(
            {
                "version": "data-demand-intent-v2",
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
                        json_bytes(root["original_source"]),
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
                "discovery": [
                    {
                        key: value
                        for key, value in asdict(item).items()
                        if key != "target_role" or value is not None
                    }
                    for item in discovery
                ],
                "inference": inference,
                "execution_profile": execution_profile,
            }
        )
    )


@dataclass(frozen=True)
class BoundDataRequest:
    """A sufficient frozen native-read binding, before request attachment."""

    obligation: str
    operation: str
    subject: str
    request: bytes
    request_id: str
    admission: bytes
    binding: bytes
    resolved: ResolvedOperationBinding
    binding_result: BindingResult


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


class FulfilledUseRecipient(TypedDict):
    """A declared output-to-input role occurrence selected by the native routine."""

    selection_name: str
    selection_generation: int
    use_id: str
    producer_operation: str
    output_role: str
    output_position: int
    recipient_obligation: str
    recipient_operation: str
    input_role: str
    successor_use_id: str | None
    successor_fate: Literal["pending", "attached", "fulfilled"]


def _population_context_matches(
    row: dict,
    obligation: dict,
    *,
    source_set: str | None,
    source_sets: dict,
    project: str,
    original_source_role: bool = False,
    discovery: tuple[dict, ...] = (),
) -> bool:
    """Use authenticated contexts, or an explicitly frozen exact member association."""

    def same_context(left: dict, right: dict) -> bool:
        return all(
            left.get(key) == right[key]
            for key in ("subject", "subject_definition", "original_source")
        ) and (
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
    if source_set is None and same_context(producer, obligation):
        return True
    if (
        original_source_role
        and row.get("complete") is True
        and producer.get("original_source") == obligation["original_source"]
        and all(
            isinstance(evidence.get(key), str) and evidence[key]
            for key in ("product_id", "derivation_id", "admission_use_id", "member_role")
        )
        and any(
            relation["target"] == obligation["operation_id"]
            and relation["producer"] == producer["operation_id"]
            and relation["output_role"] == evidence["member_role"]
            and relation["population"] == row["name"]
            and relation.get("target_role") is None
            for relation in discovery
        )
        and any(same_context(member, obligation) for member in row["members"])
    ):
        # Native close_data_population authenticates same project, released
        # producer/output, derivation/use and complete membership. An exact
        # child in that closure permits the declared original-source role to
        # consume the whole context population; it does not create a subset.
        return True
    if source_set is None:
        return False
    scope = source_sets.get(source_set)
    if scope is None:
        return False
    if scope["acquisition"]["kind"] == "selected-support-v1" and not any(
        proof["product_id"] == evidence.get("product_id")
        and proof["support"]["derivation_id"] == evidence.get("derivation_id")
        and proof["support"]["admission_use_id"] == evidence.get("admission_use_id")
        and proof["output"]["role"] == evidence.get("member_role")
        for read in scope["acquisition"]["reads"]
        for proof in read["proofs"]
    ):
        return False
    members = {member["member_id"]: member for member in row["members"]}
    return any(
        entry["project_id"] == project
        and entry["product"] == evidence["product_id"]
        and entry["original_source"] == producer.get("original_source")
        and entry["member"] in members
        and same_context(entry, members[entry["member"]])
        for entry in source_sets.get(source_set, {}).get("entries", ())
    )


class ResumedDataDemand(WireReadDemandResultResult):
    completion_inspections: dict[str, WireInspectDataCompletionResult]


class DemandPlanner:
    """Advance a native Demand from compiled SQL bindings in bounded batches."""

    def __init__(self, model: EffectiveDataOperationModel, storage: DataOperationStorage):
        self.model = model
        self.storage = storage
        self.selected_population_ids: tuple[str, ...] = ()
        self.fulfilled_request_ids: tuple[str, ...] = ()
        self.logical_progress = 0
        self.refusals: tuple[Exception, ...] = ()

    def register(
        self,
        intent: DemandIntent,
        *,
        project: str,
        release: str,
        runtime: str,
        strength: str = "value",
    ) -> WireRegisterDataDemandResult:
        record = intent.record
        if record["model"] != sha256(self.model.content).hexdigest():
            raise ValueError("demand intent belongs to a different effective model")
        result = self.storage.register_data_demand(
            {
                "project_id": ProjectId(project),
                "release_id": ReleaseId(release),
                "runtime_id": RuntimeId(runtime),
                "root": record["roots"],
                "selection": record,
                "strength": cast(Literal["episode", "independent", "value"], strength),
            }
        )
        if result.get("state") == "cancelled":
            return result
        for name, source in record.get("original_sources", {}).items():
            payload = {
                "demand_id": result["demand_id"],
                "selection_name": name,
                **source,
            }
            if source["reference"].get("kind") == "authored-fact":
                self.storage.admit_authored_data(cast(WireAdmitAuthoredDataRequest, payload))
            elif source["reference"].get("kind") == "original-document":
                self.storage.admit_original_document_asset(
                    cast(WireAdmitOriginalDocumentAssetRequest, payload)
                )
            else:
                raise ValueError("unknown original source admission reference")
        return result

    def resume(
        self,
        demand: str,
        selection: Mapping[str, Any] | None = None,
        *,
        limit: int = 100,
        after: str | None = None,
        trust_snapshot: dict | None = None,
        read_id: str | None = None,
    ) -> ResumedDataDemand:
        if type(limit) is not int or not 1 <= limit <= 1000:
            raise ValueError("demand frontier limit must be between one and 1000")
        request: WireReadDemandResultRequest = {"demand_id": WireDemandId(demand), "limit": limit}
        if selection is not None:
            request["selection"] = cast(WireDemandIntent, selection)
        if after is not None:
            request["after"] = WireObligationId(after)
        if trust_snapshot is not None:
            request["trust_snapshot"] = trust_snapshot
        if read_id is not None:
            request["read_id"] = WireReadIdentity(read_id)
        snapshot = self.storage.read_demand_result(request)
        frozen = snapshot["intent"]
        if frozen["model"] != sha256(self.model.content).hexdigest():
            raise ValueError("resume requires the demand's original effective model")
        # Inspect uncertain completions before returning any executable work.
        inspections: dict[str, WireInspectDataCompletionResult] = {}
        inspected = set()
        for obligation in snapshot["obligations"]:
            intent_id = obligation.get("intent_id")
            binding = (
                intent_id,
                demand,
                obligation.get("request_id"),
                obligation.get("generation"),
            )
            if intent_id is not None and binding not in inspected:
                inspected.add(binding)
                inspections[intent_id] = self.storage.inspect_data_completion(
                    cast(
                        WireInspectDataCompletionRequest,
                        {
                            "intent_id": obligation["intent_id"],
                            "demand_id": demand,
                            "request_id": obligation["request_id"],
                            "generation": obligation["generation"],
                        },
                    )
                )
        # These are current receipt observations, distinct from the pinned frontier.
        # Returning them lets the execution owner settle uncertainty without inference.
        return {**snapshot, "completion_inspections": inspections}

    def settle_pending_discovery(self, snapshot: ResumedDataDemand) -> bool:
        producers = {relation["producer"] for relation in snapshot["intent"]["discovery"]}
        page = [
            row["obligation_id"]
            for row in snapshot["obligations"]
            if row["operation_id"] in producers and row["fate"] == "fulfilled"
        ]
        if not page:
            return False
        return bool(
            self.storage.connection.scalar(
                select(
                    func.ops.ddo_settle_pending_discovery(
                        snapshot["read_id"],
                        bindparam("discovery_page", page, type_=ARRAY(Text())),
                    )
                )
            )
        )

    def _fulfilled_use_recipients(
        self,
        snapshot: Mapping[str, Any],
        page: list[str],
        *,
        after_wait: bool = False,
    ) -> tuple[FulfilledUseRecipient, ...]:
        if not page:
            return ()
        query = select(
            func.ops.ddo_fulfilled_use_recipients(
                snapshot["project_id"],
                snapshot["read_id"],
                bindparam("dispatch_page", page, type_=ARRAY(Text())),
                after_wait,
                type_=JSONB(),
            )
        )
        return tuple(
            cast(FulfilledUseRecipient, reason) for reason in self.storage.connection.scalars(query)
        )

    def ready(
        self,
        snapshot: Mapping[str, Any],
        *,
        authorization: bytes,
        excluded_requests: frozenset[tuple[str, int]] = frozenset(),
    ) -> tuple[ReadyDataRequest, ...]:
        from .refusal_types import SemanticRefusal

        ready = []
        self.logical_progress = 0
        self.refusals = ()
        selected = {item["operation"]: item for item in snapshot["intent"]["operations"]}
        obligations = {item["obligation_id"]: item for item in snapshot["obligations"]}
        woken = frozenset(
            reason["recipient_obligation"]
            for reason in self._fulfilled_use_recipients(
                snapshot,
                [
                    key
                    for key, obligation in obligations.items()
                    if obligation["fate"] == "awaiting-inputs"
                ],
                after_wait=True,
            )
            if reason["successor_fate"] == "pending"
        )
        rebindings = {}
        for use in snapshot.get("uses", ()):
            if use.get("rebind_derivation"):
                rebindings.setdefault(
                    (use.get("obligation_id"), use.get("request_id")), use["rebind_derivation"]
                )
        bounds = tuple(
            self.bound_requests(
                snapshot,
                authorization=authorization,
                excluded_requests=excluded_requests,
                woken_obligations=woken,
            )
        )
        items = []
        for bound in bounds:
            obligation = obligations[bound.obligation]
            operation = selected[bound.operation]
            rebind = rebindings.get((obligation["obligation_id"], bound.request_id))
            items.append(
                cast(
                    WireAttachDataRequestsItem,
                    {
                        **({"rebind_derivation": rebind} if rebind is not None else {}),
                        "obligation_id": obligation["obligation_id"],
                        "request_meaning": json.loads(bound.request),
                        "request_key": bound.request_id,
                        "binding": interpret_wire_record(
                            "binding", native_json_loads(bound.binding)
                        ),
                        "replicate": operation["replicate"],
                    },
                )
            )
        if not items:
            return ()
        attached = self.storage.attach_data_requests(
            cast(
                WireAttachDataRequestsRequest,
                {
                    "read_id": snapshot["read_id"],
                    "items": items,
                },
            )
        )["items"]
        if len(attached) != len(bounds):
            raise SemanticRefusal("native attach set changed its item correspondence")
        for bound, item in zip(bounds, attached, strict=True):
            if item["state"] == "refused":
                error = SemanticRefusal("native attachment refused: " + item["reason"])
                error.add_note(
                    "native obligation: " + bound.obligation + "; SQLSTATE " + item["sqlstate"]
                )
                self.refusals += (error,)
                continue
            native = item["result"]
            obligation = obligations[bound.obligation]
            if (obligation.get("request_id"), obligation.get("generation"), obligation["fate"]) != (
                native["request_id"],
                native["generation"],
                native["fate"],
            ):
                self.logical_progress += 1
            if item["state"] == "fulfilled":
                self.fulfilled_request_ids += (native["request_id"],)
                continue
            ready.append(
                ReadyDataRequest(
                    **{name: value for name, value in vars(bound).items() if name != "request_id"},
                    native=canonical_bytes(native),
                )
            )
        return tuple(ready)

    def bound_requests(
        self,
        snapshot: Mapping[str, Any],
        *,
        authorization: bytes,
        retained: bool = False,
        excluded_requests: frozenset[tuple[str, int]] = frozenset(),
        woken_obligations: frozenset[str] = frozenset(),
    ):
        self.selected_population_ids = ()
        self.fulfilled_request_ids = ()
        if snapshot.get("state") == "cancelled":
            return ()

        from .data_operation_bindings import (
            BindingReason,
            PopulationBinding,
            compile_binding,
            execute_binding,
            recordable_binding_fate,
        )
        from .data_operation_storage import admitted_data_projection
        from .data_operation_values import decode_semantic_value, semantic_value

        if snapshot.get("state") == "cancelled":
            return ()

        frozen = snapshot["intent"]
        if frozen["model"] != sha256(self.model.content).hexdigest():
            raise ValueError("binding requires the demand's retained model")
        selected = {item["operation"]: item for item in frozen["operations"]}
        source_sets = frozen.get("source_sets", {})
        latest_uses = {use["obligation_id"]: use for use in snapshot.get("uses", ())}
        for obligation in snapshot["obligations"]:
            if (obligation.get("request_id"), obligation.get("generation")) in excluded_requests:
                continue
            if obligation["fate"] in {"fulfilled", "closed", "cancelled", "failed"}:
                continue
            previous = latest_uses.get(obligation["obligation_id"])
            native_readiness = obligation.get("native_readiness")
            if not retained and native_readiness is not None and not native_readiness["ready"]:
                continue
            if (
                native_readiness is None
                and not retained
                and obligation["obligation_id"] not in woken_obligations
                and not obligation.get("binding_authority_changed")
                and not obligation.get("binding_pin_changed")
                and previous is not None
                and previous["fate"]
                in {"awaiting-inputs", "awaiting-population", "awaiting-discovery"}
                and previous["selection"].get("inputs_watermark") == obligation["inputs_watermark"]
            ):
                continue
            wait_observation = {"read_id": snapshot["read_id"]}
            if "inputs_watermark" in obligation:
                wait_observation["inputs_watermark"] = obligation["inputs_watermark"]
            operation = selected[obligation["operation_id"]]
            discovery_roles = {
                relation["target_role"]: relation["population"]
                for relation in frozen["discovery"]
                if relation["target"] == operation["operation"]
                and relation.get("target_role") is not None
            }
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
                    subject_definition=self.model.operation(operation["operation"]).subject,
                ),
                subject=obligation["subject"],
                parameters=decode_semantic_value(operation["parameter_meaning"]),
                choices=operation["choices"],
                source_sets=read_source_sets(source_sets),
                original_source=obligation["original_source"],
                discovery_roles=tuple(discovery_roles.items()),
                replicate=operation["replicate"],
            )
            # Compile once without witnesses to obtain the shared AST's active
            # role/population associations, including its frozen branch choices.
            compiled = compile_binding(
                self.model,
                operation["operation"],
                projections,
                **binding_arguments,
            )
            roots = (
                *operation["dependencies"],
                *(
                    relation["producer"]
                    for relation in frozen["discovery"]
                    if relation["target"] == operation["operation"]
                ),
            )
            prerequisites = rooted_closure(
                _frozen_dependency_graph(selected, frozen["discovery"]), roots
            )
            operation_roles = {
                role.name: role
                for role in self.model.operation(operation["operation"]).roles
                if role.direction == "input"
            }
            population_rows, ambiguities, derived = {}, [], False
            population_modes = dict(compiled.population_projections)
            for role_name, population_name in compiled.population_roles:
                role = operation_roles[role_name]
                scope_name = role.support.source_set if role.support is not None else None
                contextual = [
                    row
                    for row in snapshot["populations"]
                    if (
                        role_name in discovery_roles
                        and row["name"] == discovery_roles[role_name]
                        and any(
                            member["subject"] == obligation["subject"]
                            and member["original_source"] == obligation["original_source"]
                            and json_context_meaning(json_bytes(member["analyzed_scope"]))
                            == json_context_meaning(json_bytes(obligation["analyzed_scope"]))
                            for member in row["members"]
                        )
                    )
                    or (
                        role_name not in discovery_roles
                        and _population_context_matches(
                            row,
                            obligation,
                            source_set=scope_name,
                            source_sets=source_sets,
                            project=snapshot["project_id"],
                            original_source_role=(
                                role.subject_target == "original-source"
                                and role.subject_field is not None
                            ),
                            discovery=tuple(frozen["discovery"]),
                        )
                    )
                ]
                parents = []
                for row in contextual:
                    if "selection" in row["evidence"]:
                        continue
                    producer = row["evidence"]["producer_context"]["operation_id"]
                    if producer not in prerequisites and role_name not in discovery_roles:
                        continue
                    relations = [
                        relation
                        for relation in frozen["discovery"]
                        if relation["producer"] == producer
                        and relation["population"] == row["name"]
                        and relation["output_role"] == row["evidence"]["member_role"]
                        and (
                            role_name not in discovery_roles
                            or (
                                relation["target"] == operation["operation"]
                                and relation.get("target_role") == role_name
                            )
                        )
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
                    if len(outputs) == 1 and (
                        population_modes.get(role_name) == "qualified-context"
                        or set(
                            input_kind_refinements(self.model, (role.kind,))[role.kind]
                        ).intersection(derive_member_kinds(self.model, outputs[0].kind))
                    ):
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
                if len(parents) > 1 and population_modes.get(role_name) != "qualified-context":
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
                    if retained:
                        raise ValueError(
                            "retained binding lacks its exact frozen population witness"
                        )
                    receipt = self.storage.select_data_population(
                        cast(
                            WireSelectDataPopulationRequest,
                            {
                                "obligation_id": obligation["obligation_id"],
                                "population_name": population_name,
                                "parent_population_id": parents[0]["population_id"],
                                "read_id": snapshot["read_id"],
                            },
                        )
                    )
                    self.selected_population_ids += (receipt["population_id"],)
                    derived = True
            if ambiguities:
                if retained:
                    raise ValueError("retained binding has ambiguous original population witnesses")
                self.storage.record_data_fate(
                    cast(
                        WireRecordDataFateRequest,
                        {
                            "obligation_id": obligation["obligation_id"],
                            "fate": "awaiting-population",
                            "selection": {
                                **wait_observation,
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
                                ],
                            },
                        },
                    )
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
                    projection=next(
                        population_modes[role]
                        for role, name in compiled.population_roles
                        if name == row["name"]
                    ),
                    contexts=tuple(
                        SubjectContext(
                            snapshot["project_id"],
                            member["subject"],
                            member["original_source"],
                            json_bytes(member["analyzed_scope"]),
                            subject_definition=member["subject_definition"],
                        )
                        for member in row["members"]
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
                if retained:
                    raise ValueError(
                        "retained native-read binding is no longer sufficient: " + binding.status
                    )
                self.storage.record_data_fate(
                    cast(
                        WireRecordDataFateRequest,
                        {
                            "obligation_id": obligation["obligation_id"],
                            "fate": recordable_binding_fate(binding.status),
                            "selection": {
                                **wait_observation,
                                "reasons": [asdict(reason) for reason in binding.reasons],
                            },
                        },
                    )
                )
                continue
            resolved = binding.resolved(
                subject_context=SubjectContext(
                    snapshot["project_id"],
                    obligation["subject"],
                    obligation["original_source"],
                    json_bytes(obligation["analyzed_scope"]),
                    subject_definition=self.model.operation(operation["operation"]).subject,
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
            )
            request, admission = project_operation_binding(
                self.model, resolved, execution_scope=snapshot["demand_id"]
            )
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
                            "support_derivation_ids": sorted(member.support_episodes),
                            "producer_output": (
                                member.producer_output.model_dump(mode="python")
                                if member.producer_output is not None
                                else None
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
            yield BoundDataRequest(
                obligation["obligation_id"],
                operation["operation"],
                obligation["subject"],
                request.identity.canonical_input,
                request.identity.key,
                admission.identity.canonical_input,
                canonical_bytes(wire_binding),
                resolved,
                binding,
            )
