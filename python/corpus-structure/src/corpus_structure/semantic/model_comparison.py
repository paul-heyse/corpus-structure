"""Declared model differences over checked semantic projections.

This compares two stated models. It does not inspect current source, authorize a
runtime, predict changed values or establish currentness of retained products.
"""

from __future__ import annotations

import json
from dataclasses import asdict
from hashlib import sha256
from typing import Literal

from pydantic import BaseModel, ConfigDict, JsonValue

from .data_operation_model import EffectiveDataOperationModel
from .identity import canonical_bytes


class DeclaredModelChange(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    kind: Literal["added", "removed", "changed"]
    model_ref: str
    aspect: Literal["semantic-node", "semantic-edges", "identity", "graph-projection"]
    before: JsonValue
    after: JsonValue
    consumers: tuple[str, ...]


class DeclaredModelComparison(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    version: Literal["declared-data-model-comparison-v1"] = "declared-data-model-comparison-v1"
    before_digest: str
    after_digest: str
    before_release: str | None
    after_release: str | None
    changes: tuple[DeclaredModelChange, ...]
    unknowns: tuple[str, ...]
    complete: bool


def compare_declared_models(
    before: EffectiveDataOperationModel,
    after: EffectiveDataOperationModel,
    *,
    before_release: str | None = None,
    after_release: str | None = None,
) -> DeclaredModelComparison:
    """Compare exact declared meaning and identity, with both consumer graphs.

    Relationship role, position and multiplicity remain part of each comparison.
    Diagnostic origins and source documentation belong to source comparison.
    """
    graphs = tuple(model.projection_graph("semantic-reference") for model in (before, after))
    operations = {
        operation.semantic_id for model in (before, after) for operation in model.operations
    }
    node_ids = tuple({node.id for node in model.nodes} for model in (before, after))
    changes = []

    def append(reference, aspect, old, new, *, roots):
        if old == new:
            return
        consumers = set()
        for graph, known in zip(graphs, node_ids, strict=True):
            selected = tuple(root for root in roots if root in known)
            if selected:
                consumers.update(set(graph.closure(selected, direction="dependents")) & operations)
        changes.append(
            DeclaredModelChange(
                kind="added" if old is None else "removed" if new is None else "changed",
                model_ref=reference,
                aspect=aspect,
                before=old,
                after=new,
                consumers=tuple(sorted(consumers)),
            )
        )

    old_nodes, new_nodes = ({node.id: node for node in model.nodes} for model in (before, after))
    for name in sorted(old_nodes.keys() | new_nodes.keys()):

        def record(nodes):
            node = nodes.get(name)
            return (
                None
                if node is None
                else {"category": node.category, "payload": json.loads(node.payload)}
            )

        append(name, "semantic-node", record(old_nodes), record(new_nodes), roots=(name,))

    def edges(model):
        result = {}
        for edge in model.edges:
            result.setdefault(edge.source, []).append(asdict(edge))
        # Edge collection order is not an extra relation; each record retains
        # the declared position and multiplicity, including repeated edges.
        return {
            owner: sorted(items, key=lambda item: json.dumps(item, sort_keys=True))
            for owner, items in result.items()
        }

    old_edges, new_edges = edges(before), edges(after)
    for name in sorted(old_edges.keys() | new_edges.keys()):
        append(name, "semantic-edges", old_edges.get(name), new_edges.get(name), roots=(name,))

    old_ids, new_ids = (
        {(item.owner, item.domain): item.key for item in model.identities}
        for model in (before, after)
    )
    for owner, domain in sorted(old_ids.keys() | new_ids.keys()):
        roots = (
            owner,
            *(
                operation.semantic_id
                for model in (before, after)
                for operation in model.operations
                if operation.implementation_root == owner
            ),
        )
        append(
            owner + "/" + domain,
            "identity",
            old_ids.get((owner, domain)),
            new_ids.get((owner, domain)),
            roots=roots,
        )

    old_projections, new_projections = (
        {item.name: json.loads(canonical_bytes(asdict(item))) for item in model.graph_projections}
        for model in (before, after)
    )
    for name in sorted(old_projections.keys() | new_projections.keys()):
        append(
            "graph-projection:" + name,
            "graph-projection",
            old_projections.get(name),
            new_projections.get(name),
            roots=(),
        )

    unknowns = []
    for side, model in (("before", before), ("after", after)):
        for kind in model.kinds:
            if not kind.complete:
                unknowns.append(side + ": incomplete kind " + kind.semantic_id)
        for implementation in model.implementation_slices:
            if not implementation.complete:
                unknowns.append(side + ": incomplete implementation " + implementation.root)
    return DeclaredModelComparison(
        before_digest=sha256(before.content).hexdigest(),
        after_digest=sha256(after.content).hexdigest(),
        before_release=before_release,
        after_release=after_release,
        changes=tuple(changes),
        unknowns=tuple(unknowns),
        complete=not unknowns,
    )
