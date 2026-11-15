"""Detached bounded graph observations over admitted immutable source records.

Topology is descriptive. Native selection, trust and domain validity retain their owners.
"""

from __future__ import annotations

import base64
from hashlib import sha256
from dataclasses import asdict
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from .data_operation_json import json_bytes, json_loads


class GraphNode(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    identity: str
    kind: str
    payload_json: str = "{}"


class GraphOccurrence(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    identity: str
    source: str
    target: str
    relation: str
    role: str = ""
    position: int | None = None
    multiplicity: int = Field(default=1, ge=1)
    attributes_json: str = "{}"


class GraphSnapshot(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    projection: str
    specification: str
    pins_json: str
    nodes: tuple[GraphNode, ...]
    occurrences: tuple[GraphOccurrence, ...]
    standing: Literal["complete", "partial", "unavailable"] = "complete"
    unknowns: tuple[str, ...] = ()

    @property
    def identity(self):
        return "graph-snapshot:" + sha256(json_bytes(self.model_dump())).hexdigest()


class GraphInspectionRequest(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    release_id: str
    projection: str
    project_id: str | None = None
    demand_id: str | None = None
    read_id: str | None = None
    expected_cut: str | None = None
    scope: dict = Field(default_factory=dict)
    view: Literal["members", "components", "order", "path", "boundary"] = "members"
    roots: tuple[str, ...] = ()
    target: str | None = None
    direction: Literal["dependencies", "dependents"] = "dependencies"
    cursor: str | None = None
    limit: int = Field(default=100, ge=1, le=1000)
    max_bytes: int = Field(default=262144, ge=1024, le=8388608)
    max_examined_bytes: int = Field(default=8388608, ge=1024, le=67108864)


class GraphInspectionPage(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    snapshot_id: str
    projection: str
    pins_json: str
    standing: Literal["complete", "partial", "unavailable"]
    examined_nodes: int
    examined_occurrences: int
    items: tuple[dict, ...]
    unknowns: tuple[str, ...]
    continuation: str | None = None


def inspect_graph(snapshot: GraphSnapshot, request: GraphInspectionRequest):
    from .graph_runtime import nx
    from .graph_topology import rooted_closure, boundary_edges

    if snapshot.projection != request.projection:
        raise ValueError("graph projection differs from request")
    pins = json_loads(snapshot.pins_json)
    if pins.get("release_id") != request.release_id:
        raise ValueError("graph release differs from request")
    if request.demand_id and (pins.get("demand_id"), pins.get("project_id")) != (
        request.demand_id,
        request.project_id,
    ):
        raise ValueError("graph selected context differs from request")
    unknowns = list(snapshot.unknowns)
    standing = snapshot.standing
    if len(json_bytes(snapshot.model_dump())) > request.max_examined_bytes:
        standing = "partial"
        unknowns.append("complete examined graph exceeds the requested acquisition bound")
    nodes = {node.identity: node for node in snapshot.nodes}
    if len(nodes) != len(snapshot.nodes):
        raise ValueError("graph repeats a qualified node identity")
    if len({edge.identity for edge in snapshot.occurrences}) != len(snapshot.occurrences):
        raise ValueError("graph repeats a qualified occurrence identity")
    if not set(request.roots) <= nodes.keys() or (request.target and request.target not in nodes):
        raise ValueError("graph request names an unknown node")
    if any(edge.source not in nodes or edge.target not in nodes for edge in snapshot.occurrences):
        raise ValueError("graph occurrence has an unauthenticated endpoint")
    items = []
    if standing == "complete":
        graph = nx.MultiDiGraph(backend="networkx")
        graph.add_nodes_from(sorted(nodes))
        for edge in snapshot.occurrences:
            graph.add_edge(edge.source, edge.target, key=edge.identity)
        graph = nx.freeze(graph)
        selected = (
            rooted_closure(graph, request.roots, reverse=request.direction == "dependents")
            if request.roots
            else frozenset(nodes)
        )
        viewed = nx.reverse_view(graph) if request.direction == "dependents" else graph
        if request.view == "members":
            items = [dict(kind="node", **nodes[name].model_dump()) for name in sorted(selected)]
            items.extend(
                dict(kind="occurrence", **edge.model_dump())
                for edge in snapshot.occurrences
                if edge.source in selected and edge.target in selected
            )
        elif request.view == "components":
            items = [
                dict(
                    members=sorted(component),
                    cyclic=len(component) > 1 or any(graph.has_edge(n, n) for n in component),
                )
                for component in nx.strongly_connected_components(
                    graph.subgraph(selected), backend="networkx"
                )
            ]
            items.sort(key=lambda row: row["members"])
        elif request.view == "order":
            try:
                items = [
                    dict(node=node)
                    for node in nx.lexicographical_topological_sort(
                        viewed.subgraph(selected).reverse(copy=False), key=str, backend="networkx"
                    )
                ]
            except nx.NetworkXUnfeasible:
                standing = "unavailable"
                unknowns.append("cyclic projection has no dependency order; inspect components")
        elif request.view == "path":
            if len(request.roots) != 1 or request.target is None:
                raise ValueError("path requires one root and a target")
            try:
                path = nx.shortest_path(
                    viewed, request.roots[0], request.target, weight=None, backend="networkx"
                )
                for start, end in zip(path, path[1:]):
                    original = (end, start) if request.direction == "dependents" else (start, end)
                    items.append(
                        dict(
                            source=start,
                            target=end,
                            occurrences=[
                                edge.model_dump()
                                for edge in snapshot.occurrences
                                if (edge.source, edge.target) == original
                            ],
                        )
                    )
                if len(path) == 1:
                    items = [dict(node=path[0])]
            except nx.NetworkXNoPath:
                items = []
        else:
            if not request.roots:
                raise ValueError("boundary requires an explicit selected node set")
            keys = {
                key
                for _, _, key, _ in boundary_edges(viewed, request.roots)
            }
            items = [edge.model_dump() for edge in snapshot.occurrences if edge.identity in keys]
    binding = sha256(
        json_bytes(
            dict(
                snapshot=snapshot.identity,
                request=request.model_dump(
                    exclude={"cursor", "limit", "max_bytes", "read_id", "expected_cut"}
                ),
            )
        )
    ).hexdigest()
    offset = 0
    if request.cursor:
        try:
            cursor = json_loads(base64.urlsafe_b64decode(request.cursor))
            if cursor["binding"] != binding or type(cursor["offset"]) is not int:
                raise ValueError("graph continuation differs from snapshot/request")
            offset = cursor["offset"]
            if offset < 0 or offset > len(items):
                raise ValueError("invalid graph continuation position")
        except (KeyError, TypeError, ValueError) as error:
            raise ValueError("invalid graph continuation") from error

    def page(count):
        following = offset + count
        return GraphInspectionPage(
            snapshot_id=snapshot.identity,
            projection=snapshot.projection,
            pins_json=snapshot.pins_json,
            standing=standing,
            examined_nodes=len(nodes),
            examined_occurrences=len(snapshot.occurrences),
            items=tuple(items[offset:following]),
            unknowns=tuple(unknowns),
            continuation=base64.urlsafe_b64encode(
                json_bytes(
                    dict(
                        binding=binding,
                        offset=following,
                        read_id=pins.get("read_id"),
                        cut=pins.get("cut_id"),
                    )
                )
            ).decode()
            if following < len(items)
            else None,
        )

    count = min(request.limit, len(items) - offset)
    result = page(count)
    while len(json_bytes(result.model_dump())) > request.max_bytes and count > 1:
        count -= 1
        result = page(count)
    if len(json_bytes(result.model_dump())) > request.max_bytes:
        raise ValueError("complete graph inspection item exceeds response bound")
    return result


def snapshot_from_records(projection, specification, pins, records, *, unknowns=()):
    nodes = tuple(
        sorted(
            (
                GraphNode(
                    identity=row["id"],
                    kind=row["category"],
                    payload_json=json_bytes(row["payload"]).decode(),
                )
                for row in records["nodes"]
            ),
            key=lambda node: node.identity,
        )
    )
    edges = []
    for position, row in enumerate(sorted(records["edges"], key=json_bytes)):
        edges.append(
            GraphOccurrence(
                identity="graph-occurrence:"
                + sha256(json_bytes([specification, row, position])).hexdigest(),
                source=row["source"],
                target=row["target"],
                relation=row["relation"],
                role=row.get("role", ""),
                position=row.get("position"),
                multiplicity=row.get("multiplicity", 1),
                attributes_json=json_bytes(
                    {
                        key: value
                        for key, value in row.items()
                        if key
                        not in {"source", "target", "relation", "role", "position", "multiplicity"}
                    }
                ).decode(),
            )
        )
    return GraphSnapshot(
        projection=projection,
        specification=specification,
        pins_json=json_bytes(pins).decode(),
        nodes=nodes,
        occurrences=tuple(edges),
        unknowns=tuple(unknowns),
    )


def archived_graph_snapshot(prepared, projection):
    from .data_operation_admission import bound_data_operation_model

    model = bound_data_operation_model(prepared)
    definition = model.projection_definition(projection)
    if projection in {"semantic-reference", "potential-producers", "selected-dependencies"}:
        graph = model.projection_graph(projection)
        records = (
            model.semantic_records()
            if projection == "semantic-reference"
            else {
                "nodes": [node.record() for node in model.nodes if node.id in graph.node_ids],
                "edges": [edge.record() for edge in graph.edges],
            }
        )
        return snapshot_from_records(
            projection,
            definition.identity_bytes.hex(),
            dict(release_id=prepared.release_id, model_digest=sha256(model.content).hexdigest()),
            records,
        )
    relations = {
        "lexical-reference": {"lexical_reference"},
        "possible-call": {"possible_call"},
        "resolved-definition": {"resolved_definition"},
        "type-reference": {"type_reference"},
        "implementation-determinant": None,
    }
    if projection not in relations:
        raise ValueError("runtime graph projection requires an authenticated selected demand")
    nodes, edges, unknowns = {}, [], []
    for implementation in model.implementation_slices:
        for node in implementation.nodes:
            if node.id in nodes and nodes[node.id] != node.record():
                raise ValueError("implementation projections disagree on shared node meaning")
            nodes[node.id] = node.record()
        if projection == "implementation-determinant":
            edges.extend(asdict(edge) for edge in implementation.edges)
        else:
            for fact in implementation.references:
                if fact.relation not in relations[projection]:
                    continue
                target = fact.target
                if target not in nodes:
                    target = (
                        "source-reference:"
                        + sha256(json_bytes([fact.supplying_owner, fact.target])).hexdigest()
                    )
                    nodes[target] = dict(
                        id=target,
                        category="lexical-reference"
                        if fact.relation == "lexical_reference"
                        else "unresolved-reference",
                        payload=dict(spelling=fact.target, provenance=fact.provenance),
                    )
                edges.append(
                    dict(
                        source=fact.source,
                        target=target,
                        relation=fact.relation,
                        role=fact.supplying_owner,
                        location=fact.location,
                        provenance=fact.provenance,
                    )
                )
        unknowns.extend(f"{u.source}:{u.location}: {u.reason}" for u in implementation.unknowns)
    return snapshot_from_records(
        projection,
        definition.identity_bytes.hex(),
        dict(release_id=prepared.release_id, model_digest=sha256(model.content).hexdigest()),
        dict(nodes=list(nodes.values()), edges=edges),
        unknowns=unknowns,
    )


def read_graph_inspection(connection, request: GraphInspectionRequest):
    from .releases import open_release

    if request.cursor and request.demand_id:
        try:
            cursor = json_loads(base64.urlsafe_b64decode(request.cursor))
            if not cursor.get("read_id") or not cursor.get("cut"):
                raise ValueError("selected graph cursor lacks native read pins")
            request = request.model_copy(
                update={"read_id": cursor["read_id"], "expected_cut": cursor["cut"]}
            )
        except (KeyError, TypeError, ValueError) as error:
            raise ValueError("invalid selected graph continuation") from error
    prepared = open_release(connection, request.release_id)
    if request.demand_id:
        from .selected_graph import selected_graph_snapshot

        snapshot = selected_graph_snapshot(connection, prepared, request)
    else:
        snapshot = archived_graph_snapshot(prepared, request.projection)
    return inspect_graph(snapshot, request)
