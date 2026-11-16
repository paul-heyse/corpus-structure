"""Independent facet projections over exact, retained characterization products.

Only this assessment adapter alpha-renames graph IDs. It preserves directed edges,
parallel membership and shared-node identity; it never generates complete readings.
Current selected readers compare explicit fields and graph projections. Native columns,
labels, provider schemes and raw scores retain their own meaning; a projection match
claims no linguistic truth. Numerical scoring belongs to the explicit supported task
contracts in native_scoring, separately from these field/graph comparisons.
"""

from __future__ import annotations

from collections import deque
from collections.abc import Mapping
from typing import Any

from corpus_structure.semantic.assessment_graph_contract import (
    ASSESSMENT_COLLECTIONS,
    ASSESSMENT_NODE_KINDS,
    ASSESSMENT_RELATION_KINDS,
)
from corpus_structure.semantic.identity import canonical_bytes
from corpus_structure.semantic.refusals import ReferenceError


class WitnessGraphBudgetExceeded(ReferenceError):
    """The full authenticated witness graph exceeds its requested examination bound."""


COLLECTIONS = ASSESSMENT_COLLECTIONS


def pin_key(value):
    from corpus_structure.semantic.data_product_reference import DataProductReference

    try:
        if not isinstance(value, Mapping) or set(value) != {"product_id"}:
            raise ValueError("pin fields")
        reference = DataProductReference(value["product_id"])
        return ("semantic-product", reference.product_id)
    except (ValueError, TypeError) as error:
        raise ReferenceError("assessment requires an exact current product reference") from error


def output_key(value):
    from corpus_structure.semantic.data_product_reference import (
        DataProductMemberReference,
        DataProductReference,
    )

    if not isinstance(value, Mapping) or set(value) != {"product_id", "member_id", "collection"}:
        raise ReferenceError("assessment output requires typed product/member/collection identity")
    reference = DataProductMemberReference(
        DataProductReference(value["product_id"]), value["member_id"]
    )
    if value["collection"] not in COLLECTIONS:
        raise ReferenceError("assessment output requires an actual declared collection")
    return (*pin_key(reference.product.values()), value["collection"], reference.member_id)


def _subset(actual, expected):
    if isinstance(expected, Mapping):
        return isinstance(actual, Mapping) and all(
            key in actual and _subset(actual[key], value) for key, value in expected.items()
        )
    return canonical_bytes(actual) == canonical_bytes(expected)


# Fixed semantic projections are chosen in the immutable authored case. They are
# not inferred from a grade or adjusted to hide a producer's failed fields.
_SEMANTIC_FIELDS = {
    "occurrences": {"collection", "extents"},
    "terms": {"collection", "kind", "vocabulary", "value", "status", "family"},
    "roles": {"collection", "role", "scheme", "family", "basis"},
    "memberships": {"collection", "role", "order", "scope", "structural", "family"},
    "annotations": {
        "collection",
        "kind",
        "vocabulary",
        "status",
        "native_scheme",
        "native_label",
        "family",
        "native_token",
        "formal_input",
        "formal",
        "native_mention",
        "native_edu",
        "native_boundary",
        "native_rst",
        "context",
        "model_answer",
        "navigation",
        "named_match",
    },
    "choices": {"collection", "compatibility", "family"},
    "choice_member": {"collection"},
    "named_binding": {"collection", "role", "demonstrative", "antecedent_status", "status"},
    "coverage": {
        "collection",
        "family",
        "eligible",
        "examined",
        "unexamined",
        "availability",
        "outcome",
    },
}


_NESTED_SEMANTIC_FIELDS = {
    "native_token": {
        "index",
        "text",
        "space",
        "whitespace",
        "source_role",
        "lemma",
        "pos",
        "tag",
        "morphology",
        "dependency",
        "native_head",
        "head_index_base",
        "prepared_text",
        "subword_positions",
    },
    "native_mention": {
        "coordinate_unit",
        "first",
        "last",
        "detected",
        "supplied",
        "clustered",
        "mapping_status",
        "reason",
    },
    "native_edu": {
        "mode",
        "index",
        "token_start",
        "token_end",
        "provider_start",
        "provider_end",
        "text",
    },
    "model_answer": {
        "family",
        "question_key",
        "stage",
        "answer_kind",
        "state",
        "native_answer",
        "source_field",
        "observed_keys",
        "selected_keys",
        "alternatives",
        "depends_on",
    },
    "formal_input": {
        "representation",
        "text",
        "original_text",
        "syntax_outcome",
        "interpretation_outcome",
        "symbol_outcome",
        "correspondence",
    },
    "formal": {"node_kind", "rule", "start", "end", "synthetic", "normalized"},
    "named_match": {"status"},
    "navigation": {
        "kind",
        "pointer",
        "status",
        "resolution",
        "relation_kind",
        "designator",
        "artifact_kind",
        "source_labels",
        "alias_state",
        "numbering_namespace",
        "work",
        "revision",
        "cell_index",
        "axis",
        "label",
        "measure_role",
        "geometry_role",
        "introducer",
        "definition_subject_kind",
    },
}
_ANSWER_METADATA = {
    "score",
    "scores",
    "probability",
    "probabilities",
    "logits",
    "provenance",
    "runtime",
    "runtime_id",
    "native_run",
    "request_id",
    "request_digest",
    "declaration_digest",
    "candidate_list_digest",
}


def _answer_meaning(value):
    if isinstance(value, Mapping):
        return {
            key: _answer_meaning(item) for key, item in value.items() if key not in _ANSWER_METADATA
        }
    if isinstance(value, (tuple, list)):
        return [_answer_meaning(item) for item in value]
    return value


def _nested_semantics(value):
    value = dict(value)
    for field, allowed in _NESTED_SEMANTIC_FIELDS.items():
        if field in value:
            value[field] = {key: item for key, item in value[field].items() if key in allowed}
            if field == "model_answer":
                answer = value[field]
                if "native_answer" in answer:
                    from corpus_structure.semantic.observations import source_python

                    try:
                        native = source_python(answer["native_answer"])
                    except ValueError, KeyError, TypeError:
                        native = answer["native_answer"]
                    answer["native_answer"] = _answer_meaning(native)
                if "alternatives" in answer:
                    answer["alternatives"] = [
                        {key: item for key, item in alternative.items() if key != "score"}
                        for alternative in answer["alternatives"]
                    ]
    return value


def project_graph(graph, projection):
    if projection not in {"source_semantics", "native_fidelity", "retained_identity"}:
        raise ReferenceError("graph expectations require a declared comparison projection")
    nodes = {node["id"]: node for node in graph["nodes"]}
    if len(nodes) != len(graph["nodes"]):
        raise ReferenceError("assessment graph repeats a node identity")
    retained = []
    for identity, node in nodes.items():
        value = dict(node["value"])
        edges = list(node["edges"])
        if projection == "source_semantics":
            collection = value.get("collection")
            if not isinstance(collection, str):
                raise ReferenceError("semantic graph requires a typed collection")
            allowed = _SEMANTIC_FIELDS.get(collection)
            if allowed is None:
                raise ReferenceError("semantic graph has an unknown typed collection")
            value = _nested_semantics({key: item for key, item in value.items() if key in allowed})
            if "basis" in value:
                value["basis"] = {
                    key: item
                    for key, item in value["basis"].items()
                    if key in {"kind", "status", "native_scheme", "native_label"}
                }
            edges = [
                dict(edge)
                for edge in edges
                if edge["label"]
                not in {
                    "premises",
                    "external_premises",
                    "basis.premises",
                    "basis.external_premises",
                    "named_match.native_container",
                    "named_match.nodes",
                }
            ]
            unordered = {
                "alternative",
                "required_choices",
                "required_external_choices",
                "basis.choice_refs",
                "basis.required_external_choices",
                "named_match.binding",
                "head",
                "members",
                "antecedent_members",
                "named_match.negation_occurrences",
                "navigation.roles.occurrences",
                "navigation.native_tokens.native_node",
            }
            for edge in edges:
                if edge["label"] in unordered or edge["label"] == "child":
                    edge.pop("position", None)
                if edge["label"] == "navigation.roles.occurrences":
                    edge.pop("entry", None)
                if edge.get("order") is None:
                    edge.pop("order", None)
        elif projection == "retained_identity":
            if not node.get("qualified_identity"):
                raise ReferenceError("retained identity comparison requires exact qualified nodes")
            value["qualified_identity"] = node["qualified_identity"]
        retained.append(dict(id=identity, value=value, edges=edges))
    from corpus_structure.semantic.graph_topology import rooted_closure

    from .graph_comparison import rooted_graph

    projected = dict(root=graph["root"], nodes=retained)
    selected = rooted_closure(rooted_graph(projected), (graph["root"],))
    return dict(root=graph["root"], nodes=[node for node in retained if node["id"] in selected])


def graph_equal(actual, expected, projection=None):
    """Rooted typed-graph equality with a bijection, including shared identity.

    Edge order is the projection's declared role/order sequence, not local IDs.
    The bijection prevents merging equal-spelling binders or crossing prerequisites.
    """
    try:
        if projection is not None:
            actual, expected = (
                project_graph(actual, projection),
                project_graph(expected, projection),
            )
        from .graph_comparison import comparison_mappings, rooted_graph

        return (
            next(
                comparison_mappings(
                    rooted_graph(actual), rooted_graph(expected), mode="exact", policy="exact"
                ),
                None,
            )
            is not None
        )
    except KeyError, TypeError, ValueError:
        return False


def _matches(actual, expected, graph_projection=None):
    return all(
        graph_equal(actual.get(key), value, graph_projection)
        if key == "graph"
        else key in actual and _subset(actual[key], value)
        for key, value in expected.items()
    )


def _graph_member(value):
    from corpus_structure.semantic.data_product_reference import read_member_reference

    reference = read_member_reference(value)
    return reference.product.values(), reference.member_id


class LayerProjection:
    def __init__(self, load):
        self.load = load
        self.layers = {}
        self.indexes = {}
        self.choice_groups = {}

    def layer(self, pin):
        key = pin_key(pin)
        if key not in self.layers:
            body = self.load(pin)
            self.layers[key] = body
            index = {}
            for collection in COLLECTIONS:
                for row in body.get(collection, ()):
                    local = (
                        "@coverage:" + row["family"]
                        if collection == "coverage"
                        else row["local_id"]
                    )
                    if local in index:
                        raise ReferenceError("layer has ambiguous local identity")
                    index[local] = (collection, row)
                    if collection == "annotations" and row.get("named_match"):
                        for position, binding in enumerate(row["named_match"].get("bindings", ())):
                            index[("named_binding", local, position)] = ("named_binding", binding)
                    if collection == "choices":
                        for member in row["members"]:
                            if member["local_id"] in index:
                                raise ReferenceError("layer repeats choice member identity")
                            index[member["local_id"]] = ("choice_member", member)
                            self.choice_groups[(*key, member["local_id"])] = row["local_id"]
            for run in body.get("native_runs", ()):
                if run["local_id"] in index:
                    raise ReferenceError("layer repeats native run identity")
                index[run["local_id"]] = ("native_runs", run)
            self.indexes[key] = index
        return self.layers[key]

    def project(self, output, *, include_graph=True):
        output_key(output)
        pin = {"product_id": output["product_id"]}
        body = self.layer(pin)
        identifier = output["member_id"]
        local = "@coverage:" + identifier if output["collection"] == "coverage" else identifier
        pair = self.indexes[pin_key(pin)].get(local)
        if pair is None or pair[0] != output["collection"]:
            raise ReferenceError("frozen characterization output is absent")
        collection, row = pair
        occurrences = body.get("occurrences", ())
        by_occurrence = {v["local_id"]: v["extents"] for v in occurrences}
        extents = (
            row["extents"]
            if collection == "occurrences"
            else [e for occurrence in row.get("occurrences", ()) for e in by_occurrence[occurrence]]
        )
        result = dict(
            reference=output,
            collection=collection,
            native_provider=_native_provider(body, row),
            families=[row["family"]]
            if "family" in row
            else [item["family"] for item in body.get("coverage", ())],
            extents=[
                {
                    k: e[k]
                    for k in ("source_view_id", "projection", "native_pointer", "start", "end")
                    if k in e
                }
                for e in extents
            ],
            value={k: v for k, v in row.items() if k != "local_id"},
        )
        if include_graph:
            result["graph"] = self.graph(pin, local)
        return result

    def graph(self, pin, local_id, *, max_bytes=None, witness_closure=False):
        graph = self.graph_many(
            ((pin, local_id),), max_bytes=max_bytes, witness_closure=witness_closure
        )
        return dict(root=graph["root"], nodes=graph["nodes"])

    def graph_many(self, roots, *, max_bytes=None, witness_closure=False) -> dict[str, Any]:
        roots = list(roots)
        if not roots:
            return dict(root=None, roots=[], nodes=[])
        initial = (*pin_key(roots[0][0]), roots[0][1])
        unique = {(*pin_key(pin), local): (pin, local) for pin, local in roots}
        queue = deque(unique.values())
        names = {identity: f"n{index}" for index, identity in enumerate(unique)}
        nodes = []
        remaining = max_bytes
        while queue:
            current_pin, identity = queue.popleft()
            key = pin_key(current_pin)
            self.layer(current_pin)
            collection, row = self.indexes[key][identity]
            edges = []
            value = {"collection": collection}

            def edge(label, target, target_pin=current_pin, edges=edges, **fields):
                self.layer(target_pin)
                q = (*pin_key(target_pin), target)
                if target not in self.indexes[pin_key(target_pin)]:
                    raise ReferenceError("graph witness is absent from exact closure")
                if q not in names:
                    names[q] = f"n{len(names)}"
                    queue.append((target_pin, target))
                if label not in ASSESSMENT_RELATION_KINDS:
                    raise ReferenceError(
                        "witness relation is outside the admitted assessment projection"
                    )
                edges.append(dict(label=label, target=names[q], **fields))

            if witness_closure and collection == "choice_member":
                edge("choice_group", self.choice_groups[(*key, identity)])
            for name, data in sorted(row.items()):
                if name == "local_id":
                    continue
                if name in {"owner", "member", "group", "root"}:
                    edge(name, data)
                elif name in {"occurrences", "premises", "required_choices"}:
                    for position, target in enumerate(data):
                        edge(name, target, position=position)
                elif name in {"external_premises", "required_external_choices"}:
                    for position, target in enumerate(data):
                        target_pin, target_member = _graph_member(target)
                        edge(name, target_member, target_pin, position=position)
                elif name == "head" and collection == "named_binding":
                    target_pin, target_member = _graph_member(data)
                    edge(name, target_member, target_pin)
                elif name in {"members", "antecedent_members"} and collection == "named_binding":
                    for position, target in enumerate(data):
                        target_pin, target_member = _graph_member(target)
                        edge(name, target_member, target_pin, position=position)
                elif name in {"native_token", "native_mention", "native_edu"} and witness_closure:
                    detail = dict(data)
                    for field in ("native_run", "container", "sentence"):
                        target = detail.pop(field, None)
                        if target is not None:
                            edge(name + "." + field, target)
                    value[name] = detail
                elif name == "named_match":
                    match = dict(data)
                    container = match.pop("native_container", None)
                    if container is not None:
                        edge(
                            "named_match.native_container",
                            _graph_member(container)[1],
                            _graph_member(container)[0],
                        )
                    for position, target in enumerate(match.pop("nodes", ())):
                        edge(
                            "named_match.nodes",
                            _graph_member(target)[1],
                            _graph_member(target)[0],
                            position=position,
                        )
                    for position, _ in enumerate(match.pop("bindings", ())):
                        edge(
                            "named_match.binding",
                            ("named_binding", identity, position),
                            position=position,
                        )
                    for position, target in enumerate(match.pop("negation_occurrences", ())):
                        edge("named_match.negation_occurrences", target, position=position)
                    value[name] = match
                elif name == "navigation":
                    detail = dict(data)
                    for field in ("roles", "source_labels"):
                        if field not in detail:
                            continue
                        retained = []
                        for position, item in enumerate(detail[field]):
                            metadata = {
                                key: value for key, value in item.items() if key != "occurrences"
                            }
                            for occurrence_position, target in enumerate(
                                item.get("occurrences", ())
                            ):
                                edge(
                                    "navigation." + field + ".occurrences",
                                    target,
                                    position=occurrence_position,
                                    entry=position,
                                    **metadata,
                                )
                            retained.append(metadata)
                        detail[field] = retained
                    if "native_tokens" in detail:
                        retained = []
                        for position, token in enumerate(detail["native_tokens"]):
                            metadata = {
                                key: value for key, value in token.items() if key != "native_node"
                            }
                            target = token["native_node"]
                            edge(
                                "navigation.native_tokens.native_node",
                                _graph_member(target)[1],
                                _graph_member(target)[0],
                                position=position,
                                **metadata,
                            )
                            retained.append(metadata)
                        detail["native_tokens"] = retained
                    value[name] = detail
                elif name in {"formal_input", "formal"}:
                    detail = dict(data)
                    if name == "formal_input" and "correspondence" in detail:
                        retained = []
                        for position, correspondence in enumerate(detail["correspondence"]):
                            metadata = {
                                key: value
                                for key, value in correspondence.items()
                                if key != "source_occurrences"
                            }
                            for occurrence_position, target in enumerate(
                                correspondence.get("source_occurrences", ())
                            ):
                                edge(
                                    "formal_input.correspondence.source_occurrences",
                                    target,
                                    position=occurrence_position,
                                    correspondence=position,
                                    **metadata,
                                )
                            retained.append(metadata)
                        detail["correspondence"] = retained
                    for field in (
                        ("parent_occurrence",)
                        if name == "formal_input"
                        else ("input_id", "symbol_parent")
                    ):
                        target = detail.pop(field, None)
                        if target is not None:
                            edge(name + "." + field, target)
                    value[name] = detail
                elif name == "scope" and isinstance(data, str) and data in self.indexes[key]:
                    edge(name, data)
                elif name == "basis":
                    basis = dict(data)
                    for field in ("premises", "choice_refs"):
                        for position, target in enumerate(basis.pop(field, ())):
                            edge("basis." + field, target, position=position)
                    for field in ("external_premises", "required_external_choices"):
                        for position, target in enumerate(basis.pop(field, ())):
                            edge(
                                "basis." + field,
                                _graph_member(target)[1],
                                _graph_member(target)[0],
                                position=position,
                            )
                    value[name] = basis
                elif name == "children":
                    for position, target in enumerate(
                        sorted(data, key=lambda e: (e.get("order", 0), e["role"]))
                    ):
                        edge(
                            "child",
                            target.get("target") or target["choice_group"],
                            role=target["role"],
                            structural=target["structural"],
                            order=target.get("order"),
                            position=position,
                        )
                elif name == "members" and collection == "choices":
                    # Alternative order is part of this explicit projection. Authors may
                    # declare permissible graph alternatives without dropping correlation.
                    for position, target in enumerate(data):
                        edge("alternative", target["local_id"], position=position)
                else:
                    value[name] = data
            qualified = (
                dict(product_id=current_pin["product_id"], member_id=identity)
                if isinstance(identity, str)
                else dict(
                    product_id=current_pin["product_id"],
                    member_id=identity[1],
                    path=["named_match", "bindings", identity[2]],
                )
            )
            if collection not in ASSESSMENT_NODE_KINDS:
                raise ReferenceError(
                    "witness node kind is outside the admitted assessment projection"
                )
            node = dict(
                id=names[(*key, identity)],
                qualified_identity=qualified,
                value=value,
                edges=edges,
            )
            if remaining is not None:
                remaining -= len(canonical_bytes(node)) + 1
                if remaining < 0:
                    raise WitnessGraphBudgetExceeded(
                        "operation author witness graph exceeds byte bound"
                    )
            nodes.append(node)
        return dict(
            root=names[initial],
            roots=[names[(*pin_key(pin), local)] for pin, local in roots],
            nodes=nodes,
        )


_EXTENT_FIELDS = {"source_view_id", "projection", "native_pointer", "start", "end"}


def _native_provider(body, row):
    identity = row.get("native_token", {}).get("native_run")
    return next(
        (run["provider"] for run in body.get("native_runs", ()) if run["local_id"] == identity),
        None,
    )
