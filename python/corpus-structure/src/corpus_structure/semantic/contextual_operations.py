"""Admitted contextual products using the existing exact PostgreSQL ranking kernel."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from .identity import canonical_bytes
from .types import SourceArtifact, SourceBundle

_ROOT = Path(__file__).parents[1]
_MODEL = _ROOT / "model/semantic/data-operation-contextual.yaml"
_FILES = ("methods/contextual_declared.py", "semantic/contextual_operations.py", "semantic/contextual_retrieval.py", "semantic/contextual_links.py", "semantic/contextual_storage.py", "methods/contextual_embeddings.py")


def contextual_inputs(bundle):
    import yaml

    from .declared_candidate_products import candidate_inspection_inputs

    bundle = candidate_inspection_inputs(bundle)
    name, root = "data_operation_contextual", "data_operation_contextual_root"
    existing = {source.name: source.content for source in bundle.sources}
    if name in existing:
        if existing[name] != _MODEL.read_bytes():
            raise ValueError("contextual schema differs from its acquired owner")
        return bundle
    if root in existing:
        raise ValueError("contextual inputs use their reserved schema root")
    return SourceBundle(root, (*bundle.sources, SourceArtifact(name, _MODEL.read_bytes()), SourceArtifact(root, yaml.safe_dump({"id": "urn:corpus:contextual-root", "name": root, "imports": [bundle.root, name]}).encode())))


def contextual_retrieval_assets():
    return SourceArtifact("contextual/retrieval-assets", canonical_bytes({"version": "declared-contextual-retrieval-1", "schema": _MODEL.read_bytes().hex(), "files": [(name, (_ROOT / name).read_bytes().hex()) for name in _FILES]}))


def contextual_operation_sources():
    from .python_operation_sources import PythonSource, PythonSourceCollection

    return PythonSourceCollection(tuple(PythonSource("corpus_structure." + name.removesuffix(".py").replace("/", "."), (_ROOT / name).read_bytes(), str((_ROOT / name).resolve())) for name in _FILES[:2]), boundary_contracts=(contextual_retrieval_assets(),))


def admitted_contextual_inventory(value):
    """Rebuild eligibility and semantic grouping from its one captured inventory meaning."""
    from pydantic import TypeAdapter

    from .contextual_retrieval import FrozenInventory, freeze_inventory
    from .observations import source_python

    selected = TypeAdapter(FrozenInventory).validate_python(source_python(value["inventory"]))
    meanings = {member: group.meaning for group in selected.semantic_groups for member in group.member_target_ids}
    rebuilt = freeze_inventory(selected.targets, source_selection=selected.source_selection, scope=selected.scope, effective_version=selected.effective_version, reliable_type=selected.reliable_type, parent=selected.parent, semantic_targets=meanings)
    if rebuilt != selected:
        raise ValueError("contextual inventory changes frozen eligibility or semantic membership")
    return rebuilt


def contextual_retrieval_values(connection, query, inventory, vectors, policy, *, check_active=lambda: None):
    from pydantic import TypeAdapter

    from corpus_structure.methods.contextual_embeddings import EncodedVector, EncoderProfile, identity, validate_vector

    from .contextual_links import RelationshipConstraint, RelationshipWitness, select_relationships
    from .contextual_retrieval import retrieve_candidates
    from .contextual_storage import transient_vector_relation
    from .observations import source_python, source_value

    selected = admitted_contextual_inventory(inventory)
    profile = TypeAdapter(EncoderProfile).validate_python(source_python(vectors["profile"]))
    values = TypeAdapter(tuple[EncodedVector, ...]).validate_python(source_python(vectors["vectors"]))
    if len(values) > profile.max_items or len(selected.targets) + 1 > profile.max_items:
        raise ValueError("contextual selected vector population exceeds the captured encoder bound")
    by_id = {vector.object_id: vector for vector in values}
    if len(by_id) != len(values) or query["occurrence_id"] in selected.target_ids or set(by_id) != {*selected.target_ids, query["occurrence_id"]}:
        raise ValueError("contextual vectors differ from exact selected target/query membership")
    encoded = by_id[query["occurrence_id"]]
    if encoded.vector_id != query["query_vector_id"] or encoded.source_binding != query["source_pin"]["source"]:
        raise ValueError("contextual query vector differs from its retained source occurrence")
    for vector in values:
        validate_vector(vector.values, profile.dimension)
        if vector.profile_id != profile.profile_id or vector.vector_id != identity("context-vector", [vector.object_id, vector.source_binding, profile.profile_id, vector.input_digest, vector.representation_digest]):
            raise ValueError("contextual vector differs from its captured input/profile meaning")
    for target in selected.targets:
        vector = by_id[target.target_id]
        if (vector.source_binding, vector.representation_digest) != (target.source_binding, target.representation_digest):
            raise ValueError("contextual target vector belongs to another representation")
    check_active()
    relation = transient_vector_relation(selected, tuple(by_id[key] for key in selected.target_ids), profile_id=profile.profile_id, dimension=profile.dimension)
    candidates = retrieve_candidates(connection, occurrence_id=query["occurrence_id"], query=encoded, inventory=selected, relation=relation, lexical_query=query["lexical_query"], dimension=profile.dimension, budget=policy["budget"], channel_budget=policy["channel_budget"])
    check_active()
    constraints = TypeAdapter(tuple[RelationshipConstraint, ...]).validate_python(source_python(policy["constraints"]))
    witnesses = TypeAdapter(tuple[RelationshipWitness, ...]).validate_python(source_python(policy["witnesses"]))
    exclusions = TypeAdapter(frozenset[tuple[str, str]]).validate_python(source_python(policy["exclusions"]))
    decision = select_relationships(candidates=candidates, inventory=selected, source_binding=query["source_pin"]["source"], scope=selected.scope, effective_version=selected.effective_version, constraints=constraints, witnesses=witnesses, exclusions=exclusions)
    check_active()
    return {"version": "declared-contextual-retrieval-1", "source_pin": query["source_pin"], "anchors": query["anchors"], "inventory": source_value(asdict(selected)), "candidate_list": source_value(asdict(candidates)), "relationship_decision": source_value(asdict(decision))}


def contextual_interpretation_candidates(product):
    """Read current native alternatives without a run/task carrier or a broad Reader."""
    from .contextual_storage import project_interpretation_candidates
    from .observations import source_python

    if product["version"] != "declared-contextual-retrieval-1":
        raise ValueError("contextual consumer requires its native retrieval product")
    inventory = admitted_contextual_inventory(product)
    candidates = source_python(product["candidate_list"])
    return project_interpretation_candidates(candidates, asdict(inventory), candidates["list_id"], candidates["occurrence_id"], tuple(product["anchors"]))


def execute_retrieval_profile(receiver, query, inventory, vectors, policy):
    return receiver.execute(query, inventory, vectors, policy)


@dataclass
class ContextualRetrievalPlan:
    prepared: Any
    port: Any = None

    def plan(self, arguments, *, binding, check_active, execution_owner):
        from corpus_structure.core.method import PreparedWork

        from .data_operation_json import json_bytes
        from .data_operation_model import json_context_meaning
        from .data_operation_prepared_call import PreparedCallResult

        if binding is None or binding.subject_context is None:
            raise ValueError("contextual retrieval requires its acquired source context")
        classes = {"query": "DdoContextualQuery", "inventory": "DdoContextualInventory", "vectors": "DdoContextualVectors", "policy": "DdoContextualRetrievalPolicy"}
        values = {name: self.prepared.validate_json(class_name, json_bytes(arguments.arguments[name])).model_dump(mode="python", exclude_unset=True) for name, class_name in classes.items()}
        pin, context = values["query"]["source_pin"], binding.subject_context
        if (pin["project_id"], pin["subject"], pin["original_source"], pin["analyzed_scope_meaning"]) != (context.project_id, context.subject, context.original_source, json_context_meaning(context.analyzed_scope).decode()):
            raise ValueError("contextual query differs from its acquired source context")

        def compute():
            self.port._verify()
            check_active()
            with execution_owner.engine.begin() as connection:
                product = contextual_retrieval_values(connection, **values, check_active=check_active)
            checked = self.prepared.validate_json("DdoContextualRetrievalProduct", json_bytes(product)).model_dump(mode="python", exclude_unset=True)
            contextual_interpretation_candidates(checked)
            check_active()
            self.port._verify()
            return PreparedCallResult(checked)

        (result,) = yield (PreparedWork(lambda: execution_owner.submit_python(compute)),)
        return result


def resolve_retrieval_port(prepared, model, operation, *, identity, authorize, custody, sources):
    from corpus_structure.methods.contextual_declared import ContextualRetrievalOperation

    from .data_operation_ports import PortRefusal
    from .data_operation_prepared_call import PreparedOriginalCallPort

    selected = model.operation(operation)
    if selected.semantic_id != ContextualRetrievalOperation.__data_operation__["id"]:
        raise PortRefusal("contextual retrieval factory belongs to another operation")
    receiver = ContextualRetrievalOperation(None)
    plan = ContextualRetrievalPlan(prepared)
    port = PreparedOriginalCallPort(identity, model, selected, sources, custody, receiver.run, plan.plan, "corpus_structure.semantic.contextual_operations.ContextualRetrievalPlan.plan", authorize, (contextual_retrieval_assets(),), contextual_operation_sources(), functions=(("corpus_structure.semantic.contextual_operations.contextual_retrieval_values", contextual_retrieval_values),), requires_prepared_schema=True)
    plan.port = port
    return port


def contextual_inventory_values(selection):
    from pydantic import TypeAdapter

    from .contextual_retrieval import TargetRepresentation, freeze_inventory
    from .observations import source_python, source_value

    targets = TypeAdapter(tuple[TargetRepresentation, ...]).validate_python(source_python(selection["targets"]))
    meanings = source_python(selection["semantic_targets"])
    inventory = freeze_inventory(targets, source_selection=selection["source_selection"], scope=selection["scope"], effective_version=selection.get("effective_version"), reliable_type=selection.get("reliable_type"), parent=selection.get("parent"), semantic_targets=meanings)
    return {"inventory": source_value(asdict(inventory))}


def execute_inventory_profile(receiver, selection):
    return receiver.execute(selection)


@dataclass
class ContextualInventoryPlan:
    prepared: Any
    port: Any = None

    def plan(self, arguments, *, binding, check_active, execution_owner):
        from .data_operation_json import json_bytes
        from .data_operation_prepared_call import PreparedCallResult

        check_active()
        selected = self.prepared.validate_json("DdoContextualTargetSelection", json_bytes(arguments.arguments["selection"])).model_dump(mode="python", exclude_unset=True)
        product = contextual_inventory_values(selected)
        checked = self.prepared.validate_json("DdoContextualInventory", json_bytes(product)).model_dump(mode="python", exclude_unset=True)
        check_active()
        yield from ()
        return PreparedCallResult(checked)


def resolve_inventory_port(prepared, model, operation, *, identity, authorize, custody, sources):
    from corpus_structure.methods.contextual_declared import ContextualInventoryOperation

    from .data_operation_ports import PortRefusal
    from .data_operation_prepared_call import PreparedOriginalCallPort

    selected = model.operation(operation)
    if selected.semantic_id != ContextualInventoryOperation.__data_operation__["id"]:
        raise PortRefusal("contextual inventory factory belongs to another operation")
    receiver = ContextualInventoryOperation(contextual_inventory_values)
    plan = ContextualInventoryPlan(prepared)
    port = PreparedOriginalCallPort(identity, model, selected, sources, custody, receiver.run, plan.plan, "corpus_structure.semantic.contextual_operations.ContextualInventoryPlan.plan", authorize, (contextual_retrieval_assets(),), contextual_operation_sources(), functions=(("corpus_structure.semantic.contextual_operations.contextual_inventory_values", contextual_inventory_values),), requires_prepared_schema=True)
    plan.port = port
    return port
