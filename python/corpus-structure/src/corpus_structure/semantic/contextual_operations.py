"""Admitted contextual products using the existing exact PostgreSQL ranking kernel."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from pydantic import TypeAdapter

from corpus_structure.methods.contextual_embeddings import EncodedVector, EncoderProfile

from .contextual_links import (
    RelationshipConstraint,
    RelationshipDecision,
    RelationshipEdge,
    RelationshipWitness,
)
from .contextual_numerics import RetrievalNumericalPolicy, default_retrieval_numerics
from .contextual_retrieval import FrozenInventory, SemanticTargetGroup, TargetRepresentation
from .identity import canonical_bytes
from .python_module_projection import admitted_operation_module_meaning
from .types import SourceArtifact, SourceBundle

_ROOT = Path(__file__).parents[1]
_MODEL = _ROOT / "model/semantic/data-operation-contextual.yaml"
_FILES = (
    "methods/contextual_declared.py",
    "semantic/contextual_operations.py",
    "semantic/contextual_neighborhood.py",
    "semantic/contextual_retrieval.py",
    "semantic/contextual_numerics.py",
    "semantic/contextual_linguistics.py",
    "semantic/contextual_linguistics_native.py",
    "semantic/contextual_links.py",
    "semantic/contextual_storage.py",
    "methods/contextual_embeddings.py",
    "methods/contextual_targets.py",
    "semantic/contextual_target_products.py",
    "semantic/contextual_cpu.py",
    "methods/contextual_witnesses.py",
    "semantic/contextual_witnesses.py",
    "semantic/contextual_witness_native.py",
    "semantic/contextual_definition_native.py",
    "semantic/definition_admission_native.py",
    "methods/contextual_scoring.py",
    "semantic/contextual_scores.py",
    "semantic/contextual_scoring_native.py",
    "semantic/structural_products.py",
    "semantic/declared_structural_references.py",
    "semantic/declared_record_sources.py",
    "semantic/source_contexts.py",
    "methods/contextual_candidates.py",
    "semantic/contextual_registry.py",
)

_INVENTORY = TypeAdapter(FrozenInventory)
_PROFILE = TypeAdapter(EncoderProfile)
_VECTORS = TypeAdapter(tuple[EncodedVector, ...])
_CONSTRAINTS = TypeAdapter(tuple[RelationshipConstraint, ...])
_WITNESSES = TypeAdapter(tuple[RelationshipWitness, ...])
_EXCLUSIONS = TypeAdapter(frozenset[tuple[str, str]])
_DECISION = TypeAdapter(RelationshipDecision)
_TARGETS = TypeAdapter(tuple[TargetRepresentation, ...])


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
    return SourceBundle(
        root,
        (
            *bundle.sources,
            SourceArtifact(name, _MODEL.read_bytes()),
            SourceArtifact(
                root,
                yaml.safe_dump(
                    {
                        "id": "urn:corpus:contextual-root",
                        "name": root,
                        "imports": [bundle.root, name],
                    }
                ).encode(),
            ),
        ),
    )


def contextual_retrieval_assets():
    return SourceArtifact(
        "contextual/retrieval-assets",
        canonical_bytes(
            {
                "version": "declared-contextual-retrieval-1",
                "schema": _MODEL.read_bytes().hex(),
                "files": [
                    (
                        name,
                        (
                            admitted_operation_module_meaning((_ROOT / name).read_bytes()).hex()
                            if name
                            in (
                                "methods/contextual_declared.py",
                                "methods/contextual_targets.py",
                                "methods/contextual_scoring.py",
                                "methods/contextual_witnesses.py",
                            )
                            else (_ROOT / name).read_bytes().hex()
                        ),
                    )
                    for name in _FILES
                ],
            }
        ),
    )


def contextual_numerical_asset(numerical_policy=None):
    selected = default_retrieval_numerics() if numerical_policy is None else numerical_policy
    return SourceArtifact(
        "contextual/retrieval-numerical-policy",
        canonical_bytes({"policy": selected.model_dump(mode="json")}),
    )


def contextual_operation_declarations():
    from .contextual_neighborhood import NeighborhoodNumericalPolicy
    from .data_operation_version import MODEL_VERSION
    from .nominal_schema_kinds import nominal_schema_kinds

    return SourceArtifact(
        "contextual/retrieval-numerical-kinds",
        canonical_bytes(
            {
                "version": MODEL_VERSION,
                "kinds": nominal_schema_kinds(
                    RetrievalNumericalPolicy.model_json_schema(),
                    namespace="urn:corpus:kind:contextual-retrieval:",
                    root_name="NumericalPolicy",
                )
                + nominal_schema_kinds(
                    NeighborhoodNumericalPolicy.model_json_schema(),
                    namespace="urn:corpus:kind:contextual-neighborhood:",
                    root_name="NumericalPolicy",
                ),
            }
        ),
    )


def contextual_operation_sources(numerical_policy=None, *, neighborhood_policy=None):
    from .contextual_neighborhood import neighborhood_kernel_asset, neighborhood_numerical_asset
    from .python_operation_sources import PythonSource, PythonSourceCollection

    return PythonSourceCollection(
        tuple(
            PythonSource(
                "corpus_structure." + name.removesuffix(".py").replace("/", "."),
                (_ROOT / name).read_bytes(),
                str((_ROOT / name).resolve()),
            )
            for name in (
                *_FILES[:3],
                "methods/contextual_targets.py",
                "semantic/contextual_target_products.py",
                "semantic/contextual_cpu.py",
                "methods/contextual_scoring.py",
                "semantic/contextual_scores.py",
                "methods/contextual_witnesses.py",
                "semantic/contextual_witnesses.py",
                "semantic/data_operation_prepared_call.py",
            )
        ),
        boundary_contracts=(
            contextual_retrieval_assets(),
            contextual_numerical_asset(numerical_policy),
            neighborhood_numerical_asset(neighborhood_policy),
            neighborhood_kernel_asset(),
        ),
    )


def admitted_contextual_inventory(value):
    """Rebuild eligibility and semantic grouping from its one captured inventory meaning."""
    from .contextual_retrieval import freeze_inventory
    from .observations import source_python

    selected = _INVENTORY.validate_python(source_python(value["inventory"]))
    meanings = {
        member: group.meaning
        for group in selected.semantic_groups
        for member in group.member_target_ids
    }
    rebuilt = freeze_inventory(
        selected.targets,
        source_selection=selected.source_selection,
        scope=selected.scope,
        effective_version=selected.effective_version,
        reliable_type=selected.reliable_type,
        parent=selected.parent,
        semantic_targets=meanings,
    )
    if rebuilt != selected:
        raise ValueError("contextual inventory changes frozen eligibility or semantic membership")
    return rebuilt


@dataclass(frozen=True)
class ContextualRetrievalInputs:
    inventory: Any
    profile: Any
    query_vector: Any
    relation: Any
    constraints: tuple
    witnesses: tuple
    exclusions: frozenset


def prepare_contextual_retrieval(query, inventory, vectors, policy, *, check_active=lambda: None):
    from corpus_structure.methods.contextual_embeddings import identity, validate_vector

    from .contextual_storage import lexical_target_rows, transient_vector_relation
    from .observations import source_python

    selected = admitted_contextual_inventory(inventory)
    if canonical_bytes(source_python(vectors["lexical_targets"])) != canonical_bytes(
        lexical_target_rows(selected)
    ):
        raise ValueError("contextual lexical targets differ from their exact frozen inventory")
    profile = _PROFILE.validate_python(source_python(vectors["profile"]))
    values = _VECTORS.validate_python(source_python(vectors["vectors"]))
    if len(values) > profile.max_items or len(selected.targets) + 1 > profile.max_items:
        raise ValueError("contextual selected vector population exceeds the captured encoder bound")
    by_id = {vector.object_id: vector for vector in values}
    if (
        len(by_id) != len(values)
        or query["occurrence_id"] in selected.target_ids
        or set(by_id) != {*selected.target_ids, query["occurrence_id"]}
    ):
        raise ValueError("contextual vectors differ from exact selected target/query membership")
    encoded = by_id[query["occurrence_id"]]
    if (
        encoded.vector_id != query["query_vector_id"]
        or encoded.representation_digest != query["context"]["representation_digest"]
        or encoded.source_binding != query["source_pin"]["source"]
    ):
        raise ValueError("contextual query vector differs from its retained source occurrence")
    for vector in values:
        validate_vector(vector.values, profile.dimension)
        if vector.profile_id != profile.profile_id or vector.vector_id != identity(
            "context-vector",
            [
                vector.object_id,
                vector.source_binding,
                profile.profile_id,
                vector.input_digest,
                vector.representation_digest,
            ],
        ):
            raise ValueError("contextual vector differs from its captured input/profile meaning")
    for target in selected.targets:
        vector = by_id[target.target_id]
        if (vector.source_binding, vector.representation_digest) != (
            target.source_binding,
            target.representation_digest,
        ):
            raise ValueError("contextual target vector belongs to another representation")
    check_active()
    relation = transient_vector_relation(
        selected,
        tuple(by_id[key] for key in selected.target_ids),
        profile_id=profile.profile_id,
        dimension=profile.dimension,
    )
    constraints = _CONSTRAINTS.validate_python(source_python(policy["constraints"]))
    if "witnesses" in policy:
        raise ValueError(
            "authored relationship hypotheses require the explicit native witness binding"
        )
    witnesses = ()
    exclusions = _EXCLUSIONS.validate_python(source_python(policy["exclusions"]))
    return ContextualRetrievalInputs(
        selected, profile, encoded, relation, constraints, witnesses, exclusions
    )


def query_contextual_retrieval(connection, inputs, query, policy, *, numerical_policy=None):
    from .contextual_scores import candidates_from_scores, query_contextual_scores

    numerics = default_retrieval_numerics() if numerical_policy is None else numerical_policy
    scores = query_contextual_scores(connection, inputs, query, policy, numerical_policy=numerics)
    return candidates_from_scores(inputs, scores, query, policy, numerical_policy=numerics)


def finish_contextual_retrieval(inputs, candidates, query, *, check_active=lambda: None):
    from .contextual_links import select_relationships
    from .observations import source_value

    selected, constraints, witnesses, exclusions = (
        inputs.inventory,
        inputs.constraints,
        inputs.witnesses,
        inputs.exclusions,
    )
    check_active()
    decision = select_relationships(
        candidates=candidates,
        inventory=selected,
        source_binding=query["source_pin"]["source"],
        scope=selected.scope,
        effective_version=selected.effective_version,
        constraints=constraints,
        witnesses=witnesses,
        exclusions=exclusions,
    )
    check_active()
    return {
        "version": "declared-contextual-retrieval-1",
        "source_pin": query["source_pin"],
        "anchors": query["anchors"],
        "inventory": source_value(asdict(selected)),
        "candidate_list": source_value(asdict(candidates)),
        "relationship_decision": source_value(asdict(decision)),
    }


def contextual_retrieval_values(
    connection,
    query,
    inventory,
    vectors,
    policy,
    *,
    check_active=lambda: None,
    numerical_policy=None,
):
    """Execute under a caller-owned borrow; invocation ports release it before interpretation."""
    inputs = prepare_contextual_retrieval(
        query, inventory, vectors, policy, check_active=check_active
    )
    candidates = query_contextual_retrieval(
        connection, inputs, query, policy, numerical_policy=numerical_policy
    )
    return finish_contextual_retrieval(inputs, candidates, query, check_active=check_active)


def contextual_interpretation_candidates(product):
    """Read current native alternatives without a run/task carrier or a broad Reader."""
    from .contextual_storage import project_interpretation_candidates
    from .observations import source_python

    if product["version"] != "declared-contextual-retrieval-1":
        raise ValueError("contextual consumer requires its native retrieval product")
    inventory = admitted_contextual_inventory(product)
    candidates = source_python(product["candidate_list"])
    return project_interpretation_candidates(
        candidates,
        asdict(inventory),
        candidates["list_id"],
        candidates["occurrence_id"],
        tuple(product["anchors"]),
    )


def execute_retrieval_profile(receiver, query, inventory, vectors, policy, scores):
    return receiver.execute(query, inventory, vectors, policy, scores)


@dataclass
class ContextualRetrievalPlan:
    prepared: Any
    numerical_policy: RetrievalNumericalPolicy
    port: Any = None
    witnessed: bool = False

    def plan(self, arguments, *, binding, check_active, execution_owner):
        import inspect

        from .contextual_scores import execute_contextual_retrieval_kernel
        from .data_operation_cpu_basis import cpu_authority_value, cpu_input_basis_from_binding
        from .data_operation_json import json_bytes
        from .data_operation_prepared_call import PreparedCallResult

        if binding is None or binding.subject_context is None:
            raise ValueError("contextual retrieval requires its acquired source context")
        classes = dict(
            query="DdoContextualQuery",
            inventory="DdoContextualInventory",
            vectors="DdoContextualVectors",
            policy="DdoContextualRetrievalPolicy",
            scores="DdoContextualNativeScores",
        )
        if self.witnessed:
            classes["witnesses"] = "DdoContextualWitnessBindings"
        values = {
            name: self.prepared.validate_json(
                kind, json_bytes(arguments.arguments[name])
            ).model_dump(mode="python", exclude_unset=True)
            for name, kind in classes.items()
        }
        basis = cpu_input_basis_from_binding(
            self.port.identity.recipe, binding, {name: (value,) for name, value in values.items()}
        )
        kernel = execute_contextual_retrieval_kernel
        bound = inspect.signature(kernel).bind(
            input_basis=basis,
            numerical_policy=self.numerical_policy.model_dump(mode="json"),
            witnessed=self.witnessed,
            check_active=check_active,
        )
        reply = yield from self.port.plan_cpu_reply(
            kernel,
            bound,
            contextual_operation_sources(self.numerical_policy),
            check_active=check_active,
            execution_owner=execution_owner,
        )
        product = cpu_authority_value(reply.content, expected_basis=basis)
        checked = self.prepared.validate_json(
            "DdoContextualWitnessedRetrievalProduct"
            if self.witnessed
            else "DdoContextualRetrievalProduct",
            json_bytes(product),
        ).model_dump(mode="python", exclude_unset=True)
        contextual_interpretation_candidates(checked)
        return PreparedCallResult(
            checked,
            cpu_execution_evidence=canonical_bytes(reply.execution_receipt.record()),
            cpu_execution_reply=reply.content,
        )


def execute_witnessed_retrieval_profile(
    receiver, query, inventory, vectors, policy, scores, witnesses
):
    return receiver.execute(query, inventory, vectors, policy, scores, witnesses)


def resolve_retrieval_port(prepared, model, operation, *, identity, authorize, custody, sources):
    from corpus_structure.methods.contextual_declared import ContextualRetrievalOperation
    from corpus_structure.methods.contextual_witnesses import ContextualWitnessedRetrievalOperation

    from .contextual_scores import execute_contextual_retrieval_kernel
    from .data_operation_ports import PortRefusal
    from .data_operation_prepared_call import PreparedOriginalCallPort

    selected = model.operation(operation)
    owners = {
        kind.__data_operation__["id"]: kind
        for kind in (ContextualRetrievalOperation, ContextualWitnessedRetrievalOperation)
    }
    if selected.semantic_id not in owners:
        raise PortRefusal("contextual retrieval factory belongs to another operation")
    receiver = owners[selected.semantic_id](None)
    if selected.numerical_policy is None:
        raise PortRefusal("contextual retrieval lacks its checked numerical policy")
    numerical_policy = RetrievalNumericalPolicy.model_validate_json(selected.numerical_policy.body)
    plan = ContextualRetrievalPlan(
        prepared,
        numerical_policy,
        witnessed=selected.semantic_id == "retrieve.contextual/with-witnesses",
    )
    port = PreparedOriginalCallPort(
        identity,
        model,
        selected,
        sources,
        custody,
        receiver.run,
        plan.plan,
        "corpus_structure.semantic.contextual_operations.ContextualRetrievalPlan.plan",
        authorize,
        (contextual_retrieval_assets(), contextual_numerical_asset(numerical_policy)),
        contextual_operation_sources(numerical_policy),
        functions=(
            (
                "corpus_structure.semantic.contextual_scores.execute_contextual_retrieval_kernel",
                execute_contextual_retrieval_kernel,
            ),
        ),
        retain_cpu_reply=True,
        requires_prepared_schema=True,
    )
    plan.port = port
    return port


def contextual_inventory_values(selection):
    from .contextual_retrieval import freeze_inventory
    from .observations import source_python, source_value

    targets = _TARGETS.validate_python(source_python(selection["targets"]))
    meanings = source_python(selection["semantic_targets"])
    if not isinstance(meanings, dict) or any(
        target.type_name == "definition"
        and (
            target.target_id not in meanings
            or not isinstance(meanings[target.target_id], dict)
            or "curated_target" in meanings[target.target_id]
        )
        for target in targets
    ):
        raise ValueError(
            "native definition inventory requires actual selected semantic target meaning"
        )
    inventory = freeze_inventory(
        targets,
        source_selection=selection["source_selection"],
        scope=selection["scope"],
        effective_version=selection.get("effective_version"),
        reliable_type=selection.get("reliable_type"),
        parent=selection.get("parent"),
        semantic_targets=meanings,
    )
    return {"inventory": source_value(asdict(inventory))}


def execute_inventory_profile(receiver, selection):
    return receiver.execute(selection)


@dataclass
class ContextualInventoryPlan:
    prepared: Any
    port: Any = None

    def plan(self, arguments, *, binding, check_active, execution_owner):
        import inspect

        from .contextual_cpu import execute_contextual_projection_kernel
        from .data_operation_cpu_basis import cpu_authority_value, cpu_input_basis_from_binding
        from .data_operation_json import json_bytes
        from .data_operation_prepared_call import PreparedCallResult

        if binding is None or binding.subject_context is None:
            raise ValueError("contextual inventory requires its actual selected input basis")
        selected = self.prepared.validate_json(
            "DdoContextualTargetSelection", json_bytes(arguments.arguments["selection"])
        ).model_dump(mode="python", exclude_unset=True)
        basis = cpu_input_basis_from_binding(
            self.port.identity.recipe, binding, {"selection": (selected,)}
        )
        kernel = execute_contextual_projection_kernel
        bound = inspect.signature(kernel).bind(
            input_basis=basis,
            operation=self.port.operation.semantic_id,
            member_contract="",
            check_active=check_active,
        )
        reply = yield from self.port.plan_cpu_reply(
            kernel,
            bound,
            contextual_operation_sources(),
            check_active=check_active,
            execution_owner=execution_owner,
        )
        product = cpu_authority_value(reply.content, expected_basis=basis)
        checked = self.prepared.validate_json(
            "DdoContextualInventory", json_bytes(product)
        ).model_dump(mode="python", exclude_unset=True)
        return PreparedCallResult(
            checked,
            cpu_execution_evidence=canonical_bytes(reply.execution_receipt.record()),
            cpu_execution_reply=reply.content,
        )


def resolve_inventory_port(prepared, model, operation, *, identity, authorize, custody, sources):
    from corpus_structure.methods.contextual_declared import ContextualInventoryOperation

    from .contextual_cpu import execute_contextual_projection_kernel
    from .data_operation_ports import PortRefusal
    from .data_operation_prepared_call import PreparedOriginalCallPort

    selected = model.operation(operation)
    if selected.semantic_id != ContextualInventoryOperation.__data_operation__["id"]:
        raise PortRefusal("contextual inventory factory belongs to another operation")
    receiver = ContextualInventoryOperation(contextual_inventory_values)
    plan = ContextualInventoryPlan(prepared)
    port = PreparedOriginalCallPort(
        identity,
        model,
        selected,
        sources,
        custody,
        receiver.run,
        plan.plan,
        "corpus_structure.semantic.contextual_operations.ContextualInventoryPlan.plan",
        authorize,
        (contextual_retrieval_assets(),),
        contextual_operation_sources(),
        functions=(
            (
                "corpus_structure.semantic.contextual_cpu.execute_contextual_projection_kernel",
                execute_contextual_projection_kernel,
            ),
        ),
        requires_prepared_schema=True,
        retain_cpu_reply=True,
    )
    plan.port = port
    return port


@dataclass(frozen=True)
class ContextualRelationshipBinding:
    decision: RelationshipDecision
    edge: RelationshipEdge
    target: SemanticTargetGroup
    representations: tuple[TargetRepresentation, ...]
    source_pin: Mapping[str, Any]
    anchors: tuple[Mapping[str, Any], ...]


def contextual_relationship_binding(product, *, decision_id, edge_id):
    """Project one selected edge from an already authenticated native scalar product.

    This carries the decision and every actual target carrier; it grants no read,
    publication, component-substitution or canonical-identity authority.
    """
    from corpus_structure.methods.contextual_embeddings import identity

    from .contextual_storage import project_interpretation_candidates
    from .observations import source_python

    if product["version"] != "declared-contextual-retrieval-1":
        raise ValueError("relationship consumer requires its native retrieval product")
    inventory = admitted_contextual_inventory(product)
    raw_candidates = source_python(product["candidate_list"])
    projected = project_interpretation_candidates(
        raw_candidates,
        asdict(inventory),
        raw_candidates["list_id"],
        raw_candidates["occurrence_id"],
        tuple(product["anchors"]),
    )
    decision = _DECISION.validate_python(source_python(product["relationship_decision"]))
    meaning = {name: value for name, value in asdict(decision).items() if name != "decision_id"}
    if decision.decision_id != decision_id or decision_id != identity(
        "scoped-relationship", meaning
    ):
        raise ValueError("relationship decision differs from its exact retained identity")
    if (
        decision.candidate_list_id,
        decision.occurrence_id,
        decision.scope,
        decision.effective_version,
        decision.source_binding,
    ) != (
        projected.list_id,
        projected.occurrence_id,
        inventory.scope,
        inventory.effective_version,
        product["source_pin"]["source"],
    ):
        raise ValueError(
            "relationship decision differs from its retained source or candidate population"
        )
    edges = tuple(edge for edge in decision.selected_edges if edge.edge_id == edge_id)
    if len(edges) != 1:
        raise ValueError("relationship binding requires exactly one actually selected edge")
    edge = edges[0]
    targets = tuple(
        target for target in inventory.semantic_groups if target.target_id == edge.target_id
    )
    if (
        len(targets) != 1
        or not edge.member_target_ids
        or not set(edge.member_target_ids) <= set(targets[0].member_target_ids)
        or edge.member_target_ids
        != tuple(sorted({witness.target_id for witness in edge.witnesses}))
    ):
        raise ValueError("relationship edge substitutes its actual semantic target carriers")
    by_id = {target.target_id: target for target in inventory.targets}
    representations = tuple(by_id[identifier] for identifier in edge.member_target_ids)
    return ContextualRelationshipBinding(
        decision,
        edge,
        targets[0],
        representations,
        dict(product["source_pin"]),
        tuple(product["anchors"]),
    )
