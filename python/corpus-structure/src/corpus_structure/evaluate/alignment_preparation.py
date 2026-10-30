"""Operation-owned alignment inputs and model-derived comparison dependencies.

NetworkX is a topology projection only. Typed records retain values, occurrence paths and
alternative semantics; graph edges never aggregate numerical matching scores.
"""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Callable, Mapping
from copy import deepcopy
from dataclasses import dataclass
from types import MappingProxyType
from typing import Any

import networkx as nx

from corpus_structure.semantic.identity import canonical_bytes
from corpus_structure.semantic.reference_positions import collect_references
from corpus_structure.semantic.types import PreparedRelease

from .semantic_values import record_definition


@dataclass(frozen=True)
class OwnedSide:
    """Private snapshot: no nested source records are retained from a caller.

    These records are owned by this operation and never published for mutation. Index views
    are immutable; the canonical boundary's native list/dict representation is retained.
    """

    unit: str
    batch: Mapping[str, Any]
    context: frozenset[str]
    known_ids: Mapping[str, str]
    anchors: Mapping[str, tuple[tuple[int, int], ...]]

    @classmethod
    def from_side(cls, side):
        return cls(
            side.unit,
            MappingProxyType(deepcopy(dict(side.batch))),
            frozenset(side.context),
            MappingProxyType(dict(side.known_ids)),
            MappingProxyType(
                {key: tuple(tuple(span) for span in spans) for key, spans in side.anchors.items()}
            ),
        )


class CandidateComparisons:
    """Conservative eligible edges with dependency-directed comparison invalidation.

    Unknown dependency coverage uses an explicit global-map dependency. Failed lookups are
    nodes too: a previously absent reference becoming mapped invalidates its consumers.
    Cycles are contracted for invalidation only, never used to invent a fixed-point result.
    """

    def __init__(
        self,
        model: PreparedRelease,
        reference,
        prediction,
        entity_map,
        qualified_meaning: Callable,
        qualification_name: str,
    ):
        self.model = model
        self.reference = reference
        self.prediction = prediction
        self.qualification_name = qualification_name
        self.qualifications = (
            tuple(qualified_meaning(c.get("qualification", {})) for c in reference),
            tuple(qualified_meaning(c.get("qualification", {})) for c in prediction),
        )
        by_subject_predicate = defaultdict(list)
        for j, claim in enumerate(prediction):
            by_subject_predicate[claim["subject"], claim["predicate"]].append(j)
        self.edges = tuple(
            (i, j)
            for i, claim in enumerate(reference)
            for j in by_subject_predicate.get(
                (entity_map.get(claim["subject"]), claim["predicate"]), ()
            )
        )
        self._decisions: dict[tuple[int, int, str], Any] = {}
        self._mapping: dict[str, str] = {}
        graph: nx.DiGraph[tuple[str | int, ...]] = nx.DiGraph()
        # Values need preparation only once per reference occurrence, not once per pair.
        dependencies = {}
        for i, claim in enumerate(reference):
            found: set[tuple[str, str]] = set()
            complete = True
            for range_name, value in (
                ("Value", claim["object"]),
                (qualification_name, claim.get("qualification", {})),
            ):
                definition = record_definition(model, range_name, value)
                if definition is None:
                    complete = False
                    continue
                admitted = model.adapter(definition.name).validate_json(
                    canonical_bytes(value),
                    strict=True,
                    by_name=True,
                    context={"validation_purpose": "structural"},
                )
                found.update(
                    (ref.kind, ref.target)
                    for ref in collect_references(model, definition.name, admitted)
                )
            dependencies[i] = (frozenset(found), complete)
        for i, j in self.edges:
            pair = ("pair", i, j)
            graph.add_edge(pair, ("fact", reference[i]["id"]))
            references, complete = dependencies[i]
            for kind, target in references:
                graph.add_edge((kind, target), pair)
            if not complete:
                graph.add_edge(("global",), pair)
        # Own the graphs privately; expose no mutable attribute dictionaries.
        self._dag = nx.condensation(graph, nx.strongly_connected_components(graph))
        self._components = self._dag.graph["mapping"]

    def update(self, claim_map: Mapping[str, str]) -> None:
        changed = {
            key
            for key in self._mapping.keys() | claim_map.keys()
            if self._mapping.get(key) != claim_map.get(key)
        }
        if not changed:
            return
        components = {
            self._components[node]
            for node in [("global",), *(("fact", key) for key in changed)]
            if node in self._components
        }
        affected = set(components)
        for component in components:
            affected.update(nx.descendants(self._dag, component))
        dirty = {
            (node[1], node[2])
            for component in affected
            for node in self._dag.nodes[component]["members"]
            if node[0] == "pair"
        }
        for i, j in dirty:
            self._decisions.pop((i, j, "object"), None)
            self._decisions.pop((i, j, "qualification"), None)
        self._mapping = dict(claim_map)

    def compare(self, i, j, field, entity_map, claim_map, science_scope, equivalent):
        key = (i, j, field)
        if key in self._decisions:
            return self._decisions[key]
        if field == "object":
            left, right = self.reference[i][field], self.prediction[j][field]
            options = {
                "conditions": self.reference[i].get("qualification", {}).get("condition"),
                "range_name": "Value",
            }
        else:
            left, right = self.qualifications[0][i], self.qualifications[1][j]
            options = {"range_name": self.qualification_name}
        decision = equivalent(
            left,
            right,
            entity_map,
            claim_map,
            model=self.model,
            science_scope=science_scope,
            **options,
        )
        # Undecided may be transient (a parser/conversion timeout); it must be retried.
        if decision.outcome != "undecided":
            self._decisions[key] = decision
        return decision


def independent_assignment(weights):
    """Use component solves only when positive selected pairs have a unique optimum.

    A unique row maximum for every positive row, using distinct columns, establishes that
    all row maxima can be attained together. Otherwise preserve the original global solver,
    including its observable equal-optimum choice and zero/unmatched behavior.
    """
    import numpy as np
    from scipy.optimize import linear_sum_assignment

    if not weights.size:
        return []
    graph = nx.Graph()
    maxima = []
    for i in range(weights.shape[0]):
        js = np.flatnonzero(weights[i] > 0)
        if not len(js):
            continue
        best = np.flatnonzero(weights[i] == weights[i].max())
        if len(best) != 1:
            rows, cols = linear_sum_assignment(weights, maximize=True)
            return [(int(i), int(j)) for i, j in zip(rows, cols, strict=True) if weights[i, j] > 0]
        maxima.append(int(best[0]))
        graph.add_edges_from((("r", i), ("p", int(j))) for j in js)
    if len(set(maxima)) != len(maxima):
        rows, cols = linear_sum_assignment(weights, maximize=True)
        return [(int(i), int(j)) for i, j in zip(rows, cols, strict=True) if weights[i, j] > 0]
    pairs = []
    for component in nx.connected_components(graph):
        ri = sorted(node[1] for node in component if node[0] == "r")
        pi = sorted(node[1] for node in component if node[0] == "p")
        rows, cols = linear_sum_assignment(weights[np.ix_(ri, pi)], maximize=True)
        pairs.extend(
            (ri[int(i)], pi[int(j)])
            for i, j in zip(rows, cols, strict=True)
            if weights[ri[int(i)], pi[int(j)]] > 0
        )
    return sorted(pairs)
