"""Trusted finite execution contracts, separate from extractable domain classes.

LinkML owns the input field authority. Frozen dataclasses are normalized compiler products,
not a second validation schema. State/edge helpers validate finite declarations only; guards,
transactional authorization and effects retain their named implementations. In particular,
requiring ``execution.lifecycle.v1`` does not assert that it has been deployed.
"""

from __future__ import annotations

import json
from collections.abc import Mapping
from dataclasses import asdict, dataclass
from functools import lru_cache
from hashlib import sha256
from importlib.resources import files
from typing import Any, Never

import yaml
from linkml_runtime.utils.yamlutils import DupCheckYamlLoader
from pydantic import ValidationError

from .identity import canonical_bytes
from .types import ClassDefinition, Diagnostic, PreparationError, SourceArtifact, SourceBundle

EXECUTION_COMPILER_VERSION = "1"


@lru_cache(maxsize=1)
def approved_implementations() -> Mapping[str, Any]:
    """Resolve only application-written imports, never catalog-authored module strings."""
    from types import MappingProxyType

    from corpus_structure.orchestrate import project, semantic

    from . import (
        analytics,
        arrow_publication,
        consolidation,
        domain_operations,
        inference,
        observations,
        operations,
        prepare,
        proposals,
        publication,
        query,
        releases,
    )

    return MappingProxyType(
        {
            "prepare": prepare.prepare_release,
            "archive": releases.persist_release,
            "reload": releases.load_release,
            "activate": releases.activate_release,
            "project": project.init_bound_project,
            "start_run": operations.create_run,
            "method": operations.record_method,
            "schedule": operations.create_task,
            "claim": operations.claim_tasks,
            "complete": operations.complete_task,
            "complete_unit": operations.complete_unit_result,
            "hold": operations.hold_agent_result,
            "cut": operations.seal_cut,
            "source_execution": semantic.run_source_methods,
            "end_run": operations.end_source_run,
            "register_document": operations.register_document,
            "read_original": operations.read_original,
            "store_rendition": operations.store_rendition,
            "read_rendition": operations.read_rendition,
            "bind_report": observations.bind_result,
            "packet": proposals.proposal_packet,
            "locate": proposals.locate_proposal,
            "assemble": consolidation.assemble,
            "evaluate": domain_operations.consolidate_cut,
            "scientific_policy": domain_operations.ReleasedRulesPolicy.evaluate,
            "derive": inference.derive,
            "publish_inference": inference.publish_inference,
            "publish": publication.publish_batch,
            "native_admission": publication.admit_release,
            "read": query.read_session,
            "query": query.ReadSession.query,
            "explain": query.ReadSession.explain,
            "projection": analytics.compile_projection,
            "capture": analytics.capture_packet,
            "analysis": analytics.AnalysisScope,
            "analysis_close": analytics.AnalysisScope.close,
            "publish_arrow": arrow_publication.publish_arrow,
        }
    )


@dataclass(frozen=True)
class ExecutionModelInputs:
    schema: SourceBundle
    catalog: SourceArtifact


@dataclass(frozen=True)
class AttributeDefinition:
    name: str
    range: str
    required: bool
    multivalued: bool


@dataclass(frozen=True)
class ConceptDefinition:
    id: str
    family: str
    meaning: str
    identity: str
    scope: str
    attributes: tuple[AttributeDefinition, ...]
    relationships: tuple[str, ...]


@dataclass(frozen=True)
class EndpointRole:
    role: str
    concept: str
    minimum: int
    maximum: int | None
    ordered: bool
    unresolved: bool
    unresolved_concept: str | None


@dataclass(frozen=True)
class RelationshipDefinition:
    id: str
    kind: str
    direction: str
    endpoints: tuple[EndpointRole, ...]
    cardinality_scope: str
    identity_kind: str
    identity_roles: tuple[str, ...]
    identity_context: tuple[str, ...]
    qualifications: tuple[str, ...]
    multiplicity: str
    reference_scope: str
    invariants: tuple[str, ...]


@dataclass(frozen=True)
class StateDimension:
    id: str
    values: tuple[str, ...]


@dataclass(frozen=True)
class StateValue:
    dimension: str
    value: str


@dataclass(frozen=True)
class ComposedState:
    id: str
    values: tuple[StateValue, ...]
    terminal: bool


@dataclass(frozen=True)
class LifecycleDefinition:
    id: str
    subject: str
    dimensions: tuple[StateDimension, ...]
    states: tuple[ComposedState, ...]
    initial_states: tuple[str, ...]
    transitions: tuple[str, ...]
    invariants: tuple[str, ...]

    def state(self, values: Mapping[str, str]) -> ComposedState:
        """Resolve an exact allowed combination, without authorizing a database operation."""
        for state in self.states:
            if {v.dimension: v.value for v in state.values} == dict(values):
                return state
        _fail("invalid_composed_state", self.id, f"unsupported combination {dict(values)!r}")


@dataclass(frozen=True)
class TransitionDefinition:
    id: str
    lifecycle: str
    operation: str
    from_states: tuple[str, ...]
    to_states: tuple[str, ...]
    immutable_bindings: tuple[str, ...]
    invariants: tuple[str, ...]
    effects: tuple[str, ...]
    outcomes: tuple[str, ...]


@dataclass(frozen=True)
class InvariantDefinition:
    id: str
    meaning: str
    subjects: tuple[str, ...]
    relationships: tuple[str, ...]
    scope: str
    failure_code: str
    implementation: str
    required_capability: str | None = None


@dataclass(frozen=True)
class ImplementationBinding:
    id: str
    owner: str
    symbol: str
    version: str
    placement: str
    input_concepts: tuple[str, ...]
    result_concepts: tuple[str, ...]
    features: tuple[str, ...]
    effects: tuple[str, ...]
    required_capabilities: tuple[str, ...]


@dataclass(frozen=True)
class OperationContract:
    id: str
    inputs: tuple[str, ...]
    results: tuple[str, ...]
    applicability: tuple[str, ...]
    universe: str
    effects: tuple[str, ...]
    outcomes: tuple[str, ...]
    outcome_domain: str
    dependencies: tuple[str, ...]
    precision: str
    implementation: str
    transitions: tuple[str, ...]
    projections: tuple[str, ...]


@dataclass(frozen=True)
class ProjectionContract:
    id: str
    sources: tuple[str, ...]
    relationships: tuple[str, ...]
    universe: str
    preserves: tuple[str, ...]
    omissions: tuple[str, ...]
    precision: str
    collections: str
    completeness: str
    lifetime: str
    implementation: str


@dataclass(frozen=True)
class OutcomeDomain:
    id: str
    authority: str
    values: tuple[str, ...]


@dataclass(frozen=True)
class OutcomeTranslation:
    source_domain: str
    source: str
    target_domain: str
    target: str
    retained_meaning: str
    invariant: str


@dataclass(frozen=True)
class ExecutionModelProducts:
    model_id: str
    content: bytes
    required_capabilities: tuple[str, ...]
    concepts: tuple[ConceptDefinition, ...]
    relationships: tuple[RelationshipDefinition, ...]
    lifecycles: tuple[LifecycleDefinition, ...]
    transitions: tuple[TransitionDefinition, ...]
    operations: tuple[OperationContract, ...]
    invariants: tuple[InvariantDefinition, ...]
    implementations: tuple[ImplementationBinding, ...]
    projections: tuple[ProjectionContract, ...]
    outcome_domains: tuple[OutcomeDomain, ...]
    outcome_translations: tuple[OutcomeTranslation, ...]

    def lifecycle(self, name: str) -> LifecycleDefinition:
        return next(item for item in self.lifecycles if item.id == name)

    def validate_edge(
        self, transition: str, before: Mapping[str, str], after: Mapping[str, str]
    ) -> TransitionDefinition:
        """Check a declared finite edge. Named guards/effects still require their native owner."""
        edge = next(item for item in self.transitions if item.id == transition)
        lifecycle = self.lifecycle(edge.lifecycle)
        prior, result = lifecycle.state(before), lifecycle.state(after)
        if prior.id not in edge.from_states or result.id not in edge.to_states:
            _fail("invalid_transition", edge.id, f"unsupported edge {prior.id} -> {result.id}")
        return edge


def _fail(code: str, location: str, message: str) -> Never:
    raise PreparationError((Diagnostic(code, location, message),))


def trusted_execution_inputs() -> ExecutionModelInputs:
    """Read bundled code-owned definitions once at an explicit application entry boundary."""
    root = files("corpus_structure").joinpath("model", "semantic")
    return ExecutionModelInputs(
        SourceBundle(
            "contracts",
            (SourceArtifact("contracts", root.joinpath("contracts.yaml").read_bytes()),),
        ),
        SourceArtifact("execution-model.yaml", root.joinpath("execution-model.yaml").read_bytes()),
    )


def _plain(value: Any) -> Any:
    # DupCheckYamlLoader returns location-tagged str subclasses. Lower only those wrappers;
    # do not coerce numbers, booleans, null or other invalid authored field values.
    if isinstance(value, str):
        return str(value)
    if isinstance(value, dict):
        return {_plain(k): _plain(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_plain(v) for v in value]
    return value


def _index(items: tuple[Any, ...], location: str) -> dict[str, Any]:
    index = {item.id: item for item in items}
    if len(index) != len(items):
        _fail("duplicate_definition", location, "definition ids must be unique")
    return index


def _refs(names: tuple[str, ...], index: Mapping[str, Any], location: str) -> None:
    if len(set(names)) != len(names):
        _fail("duplicate_reference", location, "repeated reference")
    for name in names:
        if name not in index:
            _fail("unresolved_contract_reference", location, name)


def _normalize(data: dict[str, Any], model_id: str) -> ExecutionModelProducts:
    concepts = tuple(
        ConceptDefinition(
            v["id"],
            v["family"],
            v["meaning"],
            v["identity"],
            v["scope"],
            tuple(AttributeDefinition(**a) for a in v["attributes"]),
            tuple(v["relationships"]),
        )
        for v in data["concepts"]
    )
    relationships = tuple(
        RelationshipDefinition(
            v["id"],
            v["kind"],
            v["direction"],
            tuple(
                EndpointRole(
                    e["role"],
                    e["concept"],
                    e["minimum"],
                    e.get("maximum"),
                    e["ordered"],
                    e["unresolved"],
                    e.get("unresolved_concept"),
                )
                for e in v["endpoints"]
            ),
            v["cardinality_scope"],
            v["identity_kind"],
            tuple(v["identity_roles"]),
            tuple(v["identity_context"]),
            tuple(v["qualifications"]),
            v["multiplicity"],
            v["reference_scope"],
            tuple(v["invariants"]),
        )
        for v in data["relationships"]
    )
    lifecycles = tuple(
        LifecycleDefinition(
            v["id"],
            v["subject"],
            tuple(StateDimension(d["id"], tuple(d["values"])) for d in v["dimensions"]),
            tuple(
                ComposedState(
                    state["id"],
                    tuple(StateValue(**p) for p in state["values"]),
                    state["terminal"],
                )
                for state in v["states"]
            ),
            tuple(v["initial_states"]),
            tuple(v["transitions"]),
            tuple(v["invariants"]),
        )
        for v in data["lifecycles"]
    )

    def records(key: str, cls: Any) -> tuple[Any, ...]:
        return tuple(
            cls(**{k: tuple(v) if isinstance(v, list) else v for k, v in row.items()})
            for row in data[key]
        )

    products = ExecutionModelProducts(
        model_id,
        b"",
        tuple(data["required_capabilities"]),
        concepts,
        relationships,
        lifecycles,
        records("transitions", TransitionDefinition),
        records("operations", OperationContract),
        records("invariants", InvariantDefinition),
        records("implementations", ImplementationBinding),
        records("projections", ProjectionContract),
        records("outcome_domains", OutcomeDomain),
        records("outcome_translations", OutcomeTranslation),
    )
    _validate(products)
    return products


def _validate(products: ExecutionModelProducts) -> None:
    c = _index(products.concepts, "concepts")
    r = _index(products.relationships, "relationships")
    lifecycles = _index(products.lifecycles, "lifecycles")
    t = _index(products.transitions, "transitions")
    o = _index(products.operations, "operations")
    i = _index(products.invariants, "invariants")
    b = _index(products.implementations, "implementations")
    p = _index(products.projections, "projections")
    domains = _index(products.outcome_domains, "outcome_domains")
    capabilities = {name: name for name in products.required_capabilities}
    _refs(products.required_capabilities, capabilities, "required_capabilities")
    for concept in products.concepts:
        if len({a.name for a in concept.attributes}) != len(concept.attributes):
            _fail("duplicate_attribute", concept.id, "attribute names must be unique")
        for attribute in concept.attributes:
            if attribute.range not in c and attribute.range not in {
                "text",
                "integer",
                "boolean",
                "decimal",
                "datetime",
                "bytes",
                "json",
            }:
                _fail("attribute_range", concept.id, attribute.range)
        _refs(concept.relationships, r, concept.id)
    for relation in products.relationships:
        roles = {e.role: e for e in relation.endpoints}
        if len(roles) != len(relation.endpoints):
            _fail("duplicate_role", relation.id, "endpoint roles must be unique")
        for endpoint in relation.endpoints:
            _refs((endpoint.concept,), c, relation.id)
            if endpoint.maximum is not None and endpoint.maximum < endpoint.minimum:
                _fail("cardinality", relation.id, endpoint.role)
            if endpoint.unresolved != (endpoint.unresolved_concept is not None):
                _fail("unresolved_endpoint", relation.id, endpoint.role)
            if endpoint.unresolved_concept is not None:
                _refs((endpoint.unresolved_concept,), c, relation.id)
        _refs(relation.identity_roles, roles, relation.id + "/identity_roles")
        _refs(relation.qualifications, c, relation.id + "/qualifications")
        _refs(relation.invariants, i, relation.id + "/invariants")
        scoped = any(c[e.concept].scope == "realization" for e in relation.endpoints)
        required_context = (
            {"release", "realization"}
            if relation.reference_scope == "same_realization"
            else {"input_release", "input_realization", "output_release", "output_realization"}
        )
        if scoped and (
            relation.reference_scope == "execution"
            or not required_context <= set(relation.identity_context)
        ):
            _fail(
                "unqualified_reference",
                relation.id,
                "scoped references require explicit release/realization context",
            )
        if relation.identity_kind == "unordered_distinct" and relation.multiplicity != "set":
            _fail(
                "relationship_identity",
                relation.id,
                "unordered distinct identity requires set membership",
            )
    for concept in products.concepts:
        for relation in concept.relationships:
            if concept.id not in {e.concept for e in r[relation].endpoints}:
                _fail("relationship_subject", concept.id, relation)
    for invariant in products.invariants:
        _refs(invariant.subjects, c, invariant.id)
        _refs(invariant.relationships, r, invariant.id)
        _refs((invariant.implementation,), b, invariant.id)
        if invariant.required_capability is not None:
            _refs((invariant.required_capability,), capabilities, invariant.id)
    owned = approved_implementations()
    for binding in products.implementations:
        implementation = owned.get(binding.id)
        expected = (
            (
                implementation.__module__.removeprefix("corpus_structure."),
                implementation.__qualname__,
            )
            if implementation is not None
            else None
        )
        if expected != (binding.owner, binding.symbol):
            _fail("unapproved_implementation", binding.id, f"{binding.owner}:{binding.symbol}")
        _refs(binding.input_concepts, c, binding.id)
        _refs(binding.result_concepts, c, binding.id)
        _refs(binding.required_capabilities, capabilities, binding.id)
    for lifecycle in products.lifecycles:
        _refs((lifecycle.subject,), c, lifecycle.id)
        dimensions = _index(lifecycle.dimensions, lifecycle.id)
        for dimension in lifecycle.dimensions:
            if len(set(dimension.values)) != len(dimension.values):
                _fail("duplicate_state_value", lifecycle.id, dimension.id)
        states = _index(lifecycle.states, lifecycle.id)
        combinations = set()
        for state in lifecycle.states:
            values = {v.dimension: v.value for v in state.values}
            if len(values) != len(state.values) or set(values) != set(dimensions):
                _fail("state_dimensions", lifecycle.id, state.id)
            for dimension, value in values.items():
                if value not in dimensions[dimension].values:
                    _fail("state_value", lifecycle.id, f"{dimension}={value}")
            combination = tuple(sorted(values.items()))
            if combination in combinations:
                _fail("duplicate_composed_state", lifecycle.id, state.id)
            combinations.add(combination)
        _refs(lifecycle.initial_states, states, lifecycle.id)
        _refs(lifecycle.transitions, t, lifecycle.id)
        _refs(lifecycle.invariants, i, lifecycle.id)
        for edge in lifecycle.transitions:
            if t[edge].lifecycle != lifecycle.id:
                _fail("transition_lifecycle", lifecycle.id, edge)
    for transition in products.transitions:
        _refs((transition.lifecycle,), lifecycles, transition.id)
        lifecycle = lifecycles[transition.lifecycle]
        states = {state.id: state for state in lifecycle.states}
        _refs(transition.from_states, states, transition.id)
        _refs(transition.to_states, states, transition.id)
        _refs((transition.operation,), o, transition.id)
        _refs(transition.invariants, i, transition.id)
        if (
            transition.id not in lifecycle.transitions
            or transition.id not in o[transition.operation].transitions
        ):
            _fail(
                "unlinked_transition",
                transition.id,
                "lifecycle and operation must both link their edge",
            )
        if any(states[s].terminal for s in transition.from_states):
            _fail("terminal_transition", transition.id, "terminal subjects cannot reopen")
        if not set(transition.outcomes) <= set(o[transition.operation].outcomes):
            _fail("transition_outcome", transition.id, "outcome outside operation contract")
    for operation in products.operations:
        _refs(operation.inputs, c, operation.id)
        _refs(operation.results, c, operation.id)
        _refs(operation.applicability, i, operation.id)
        _refs((operation.implementation,), b, operation.id)
        _refs(operation.transitions, t, operation.id)
        _refs(operation.projections, p, operation.id)
        _refs((operation.outcome_domain,), domains, operation.id)
        domain = domains[operation.outcome_domain]
        if domain.authority == "code" and not set(operation.outcomes) <= set(domain.values):
            _fail("operation_outcome", operation.id, "outcome outside code-owned domain")
        binding = b[operation.implementation]
        if set(operation.inputs) != set(binding.input_concepts) or set(operation.results) != set(
            binding.result_concepts
        ):
            _fail(
                "implementation_contract",
                operation.id,
                "typed input/result contract differs from implementation binding",
            )
        for edge in operation.transitions:
            if t[edge].operation != operation.id:
                _fail("operation_transition", operation.id, edge)
    for projection in products.projections:
        _refs(projection.sources, c, projection.id)
        _refs(projection.relationships, r, projection.id)
        _refs((projection.implementation,), b, projection.id)
    for domain in products.outcome_domains:
        if domain.authority == "code" and not domain.values:
            _fail(
                "outcome_authority",
                domain.id,
                "code-owned outcome domain must be finite and nonempty",
            )
        if len(set(domain.values)) != len(domain.values):
            _fail("duplicate_outcome", domain.id, "outcomes must be distinct")
        if domain.authority == "release" and domain.values:
            _fail(
                "outcome_authority", domain.id, "release-authored members require the bound release"
            )
    translations = set()
    for translation in products.outcome_translations:
        _refs(
            (translation.source_domain, translation.target_domain), domains, "outcome_translation"
        )
        _refs((translation.invariant,), i, "outcome_translation")
        if (
            translation.source not in domains[translation.source_domain].values
            or translation.target not in domains[translation.target_domain].values
        ):
            _fail("translation_outcome", "outcome_translation", "unknown outcome")
        key = (translation.source_domain, translation.source, translation.target_domain)
        if key in translations:
            _fail("duplicate_translation", "outcome_translation", str(key))
        translations.add(key)


def _collection_defaults(
    name: str, body: dict[str, Any], definitions: Mapping[str, ClassDefinition]
) -> dict[str, Any]:
    """Normalize absent optional collections from the admitted schema, never nulls."""
    result = dict(body)
    for prop in definitions[name].properties:
        if prop.multivalued and not prop.required and prop.name not in result:
            result[prop.name] = []
        if prop.range in definitions and prop.name in result:
            value = result[prop.name]
            result[prop.name] = (
                [_collection_defaults(prop.range, row, definitions) for row in value]
                if prop.multivalued
                else _collection_defaults(prop.range, value, definitions)
            )
    return result


def compile_execution_model(inputs: ExecutionModelInputs) -> ExecutionModelProducts:
    """Compile only explicit immutable inputs, with bounded reuse of pure products."""
    try:
        hash(inputs)
    except TypeError:
        return _compile_execution_model(inputs)
    return _compile_execution_model_cached(inputs, EXECUTION_COMPILER_VERSION)


@lru_cache(maxsize=8)
def _compile_execution_model_cached(
    inputs: ExecutionModelInputs, compiler_version: str
) -> ExecutionModelProducts:
    return _compile_execution_model(inputs)


def _compile_execution_model(inputs: ExecutionModelInputs) -> ExecutionModelProducts:
    """Compile only supplied immutable bytes; no application defaults, imports or invocation."""
    from dataclasses import replace

    from .prepare import prepare_release

    try:
        raw = _plain(yaml.load(inputs.catalog.content, Loader=DupCheckYamlLoader))
    except Exception as exc:
        _fail("contract_catalog", inputs.catalog.name, str(exc))
    # The existing admitted LinkML profile supplies the sole field/enum/local-shape authority.
    companion = prepare_release(inputs.schema)
    try:
        data = companion.validate_json("ExecutionCatalog", json.dumps(raw)).model_dump(mode="json")
    except (ValidationError, TypeError, ValueError) as exc:
        _fail("contract_catalog", inputs.catalog.name, str(exc))
    data = _collection_defaults(
        "ExecutionCatalog", data, {d.name: d for d in companion.definitions}
    )
    identity = {
        "compiler_version": EXECUTION_COMPILER_VERSION,
        "schema": {
            "root": inputs.schema.root,
            "sources": [{"name": s.name, "sha256": s.digest} for s in inputs.schema.sources],
        },
        "catalog": {"name": inputs.catalog.name, "sha256": inputs.catalog.digest},
    }
    model_id = "execution:" + sha256(canonical_bytes(identity)).hexdigest()
    products = _normalize(data, model_id)
    normalized = {key: value for key, value in asdict(products).items() if key != "content"}
    return replace(products, content=canonical_bytes({"inputs": identity, **normalized}))
