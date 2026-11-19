"""Six statistics queries over actual selected rich facts and retained premises.

Relations project a bounded whole admission to a MultiDiGraph: entity IDs are nodes
(including isolates), each actual fact ID is a directed keyed edge of one declared
predicate, and payloads retain that fact. Parallel assertions and legal cyclic walks
remain distinct. The projection confers no additional selection or scientific truth.
"""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass

from .data_operation_json import json_bytes
from .graph_runtime import nx
from .rich_queries import (
    ConstructionProfileQuery,
    FamiliesWhereQuery,
    FamilyProfileQuery,
    ParameterMappingQuery,
    RelationsQuery,
    RichQueryIndex,
    RichQueryRefused,
    RichQueryRow,
    statement_key,
)


def _parameters(index: RichQueryIndex, subjects, facts):
    predicate = index.iri("stat:family")
    return {
        index.facts[key].subject_entity
        for key in facts
        if index.facts[key].predicate == predicate and index.object_entity(key) in subjects
    }


def _profile(index, subjects, facts):
    parameters = _parameters(index, subjects, facts)
    member = index.iri("stat:member_of_construction")
    return {
        key
        for key in facts
        if index.facts[key].subject_entity in subjects | parameters
        or (index.facts[key].predicate == member and index.object_entity(key) in subjects)
    }


def statistics_rows(index: RichQueryIndex, query):
    facts = index.included(query)
    if isinstance(query, RelationsQuery):
        yield from relation_walks(index, query)
    elif isinstance(query, FamilyProfileQuery) and query.name == "transformations_of":
        yield from transformations(index, query)
    elif isinstance(query, FamilyProfileQuery):
        wanted = _profile(index, set(index.resolve(query.family)), facts)
        for key in sorted(wanted):
            yield RichQueryRow(index.claim_record(key))
    elif isinstance(query, ConstructionProfileQuery):
        subjects = set(index.resolve(query.construction))
        wanted = _profile(index, subjects, facts)
        if query.include_suppositions:
            variables = set()
            for key in facts:
                if index.facts[key].subject_entity in subjects:
                    for occurrence in index.by_fact[key]:
                        raw = index.qualification(occurrence).model_dump(
                            mode="python", exclude_unset=True
                        )
                        if isinstance(raw.get("base_variable"), str):
                            variables.add(raw["base_variable"])
            wanted.update(key for key in facts if index.facts[key].subject_entity in variables)
        for key in sorted(wanted):
            yield RichQueryRow(index.claim_record(key))
    elif isinstance(query, ParameterMappingQuery):
        families, constructions = (
            set(index.resolve(query.family)),
            set(index.resolve(query.construction)),
        )
        wanted = _profile(index, families | constructions, facts)
        predicates = {
            index.iri("stat:" + name)
            for name in (
                "member_of_construction",
                "has_parameter",
                "identical_parameter",
                "derived_parameter",
                "parameter_role",
                "parameter_domain",
            )
        }
        member = index.iri("stat:member_of_construction")
        for key in sorted(wanted):
            fact = index.facts[key]
            if fact.predicate in predicates and (
                fact.predicate != member
                or (fact.subject_entity in families and index.object_entity(key) in constructions)
            ):
                yield RichQueryRow(index.claim_record(key))
    elif isinstance(query, FamiliesWhereQuery):
        families = {
            key
            for key, entity in index.entities.items()
            if index.is_a(entity, index.iri("DistributionFamily"))
        }
        by_subject = {identifier: {identifier} for identifier in families}
        family_predicate = index.iri("stat:family")
        for key in facts:
            if (
                index.facts[key].predicate == family_predicate
                and index.object_entity(key) in families
            ):
                by_subject.setdefault(index.facts[key].subject_entity, set()).add(
                    index.object_entity(key)
                )
        for key in facts:
            fact = index.facts[key]
            if fact.subject_entity not in by_subject or fact.predicate != index.iri(
                query.predicate
            ):
                continue
            if query.value is not None:
                definition, prop, _ = index.state.property(fact.property_contract)
                expected = index.state.prepared.property_adapter(
                    definition.name, prop.name, item=prop.multivalued
                ).validate_json(json_bytes(query.value), strict=True)
                if expected != index.object(key):
                    continue
            for family in sorted(by_subject[fact.subject_entity]):
                yield RichQueryRow(
                    dict(family=index.entity_record(family), claim=index.claim_record(key))
                )
    else:
        raise RichQueryRefused("unsupported current statistics query")


def transformations(index: RichQueryIndex, query: FamilyProfileQuery):
    families = set(index.resolve(query.family))
    distribution = index.iri("stat:has_distribution")
    for key in index.included(query):
        conclusion = index.facts[key]
        if conclusion.predicate != distribution:
            continue
        references = index.condition_refs(key, query)
        missing = references - index.facts.keys()
        if missing:
            index.unknowns[key] = dict(
                code="unresolved-premise", fact_id=key, references=sorted(missing)
            )
        known = references & index.facts.keys()
        if not any(
            index.facts[premise].predicate == distribution
            and index.object_entity(premise) in families
            for premise in known
        ):
            continue
        # Statement scope is the FULL source product/member address. A local
        # statement label or equal member string in another product is unrelated.
        statements = {
            statement_key(item.statement)
            for item in index.visible_occurrences(key, query)
            if item.statement is not None
        }
        definitions = set().union(
            *(index.definiens.get((scope, conclusion.subject_entity), ()) for scope in statements)
        )
        if not definitions:
            continue
        yield RichQueryRow(
            dict(
                conclusion=index.claim_record(key),
                premises=index.claim_records(sorted(known)),
                definiens=index.claim_records(sorted(definitions)),
                unresolved_premise_ids=sorted(missing),
                completeness="partial" if missing else "complete-within-selected-root",
            )
        )


@dataclass(frozen=True)
class RichRelationEdge:
    fact_id: str
    source: str
    target: str
    predicate: str


def relation_projection(index: RichQueryIndex, query: RelationsQuery):
    graph = nx.MultiDiGraph(backend="networkx", interpretation="rich-selected-relations-v1")
    graph.add_nodes_from(sorted(index.entities))
    predicates = {
        index.iri("stat:" + name) for name in ("special_case_of", "transformation_of", "limit_of")
    }
    for key in index.included(query):
        fact = index.facts[key]
        if fact.predicate not in predicates:
            continue
        target = index.object_entity(key)
        if target is None:
            continue
        if fact.subject_entity not in graph or target not in graph:
            raise RichQueryRefused("relation projection has an unknown actual entity endpoint")
        edge = RichRelationEdge(key, fact.subject_entity, target, fact.predicate)
        graph.add_edge(edge.source, edge.target, key=edge.fact_id, fact=edge)
    return nx.freeze(graph)


def relation_walks(index: RichQueryIndex, query: RelationsQuery):
    """Breadth-first exact witnesses; repeat vertices/edges, never deduplicate cycles.

    All roots, targets and intermediate adjacency come from the same bounded root.
    Output filtering does not alter expansion. Replay spends the same work budget;
    exceeding any bound refuses rather than returning a successful partial search.
    """
    graph = relation_projection(index, query)
    roots, targets = index.resolve(query.a), frozenset(index.resolve(query.b))
    if max(len(roots), len(targets)) > query.max_frontier:
        raise RichQueryRefused("walk root/target population exceeds the frontier bound")
    queue: deque[tuple[tuple[str, str, tuple[str, ...]], int]] = deque()
    retained = len(json_bytes(sorted(targets)))
    for root in roots:
        state = (root, root, ())
        size = len(json_bytes(state))
        queue.append((state, size))
        retained += size
    if retained > query.max_state_bytes:
        raise RichQueryRefused("walk roots/targets exceed retained-state bytes")
    examined = 0
    adjacency = {}
    while queue:
        (origin, subject, path), size = queue.popleft()
        # The graph itself is bounded by the acquired member/byte capacity. Sort
        # just this actual adjacency; keys preserve distinct parallel fact edges.
        if subject not in adjacency:
            adjacency[subject] = tuple(
                sorted(graph.out_edges(subject, keys=True, data=True), key=lambda edge: edge[2])
            )
        edges = adjacency[subject]
        for _, target, fact_id, _ in edges:
            examined += 1
            if examined > query.max_edges:
                raise RichQueryRefused("walk adjacency budget exhausted")
            witness = (*path, fact_id)
            if len(witness) < query.depth:
                child = (origin, target, witness)
                child_size = len(json_bytes(child))
                if (
                    len(queue) + 2 > query.max_frontier
                    or retained + child_size > query.max_state_bytes
                ):
                    raise RichQueryRefused("walk retained frontier capacity exhausted")
                queue.append((child, child_size))
                retained += child_size
            if target in targets:
                yield RichQueryRow(
                    dict(
                        depth=len(witness),
                        origin=origin,
                        target=target,
                        fact_ids=list(witness),
                        claims=index.claim_records(witness),
                    )
                )
        retained -= size
