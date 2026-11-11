"""Independent facet projections over exact, retained characterization products.

Only this assessment adapter alpha-renames graph IDs. It preserves directed edges,
parallel membership and shared-node identity; it never generates complete readings.
"""

from __future__ import annotations

from collections import Counter, deque
from collections.abc import Mapping
from dataclasses import asdict
from hashlib import sha256
from typing import Any

from corpus_structure.semantic.identity import canonical_bytes
from corpus_structure.semantic.product_reference import ProductReference

from .semantic import ReferenceError

COLLECTIONS = ("occurrences", "annotations", "memberships", "roles", "terms", "choices", "coverage")


def pin_key(value):
    try:
        if set(value) != {"task_id", "product_key", "content_digest"}:
            raise ValueError("pin fields")
        pin = ProductReference(**value)
        return (pin.task_id, pin.product_key, pin.content_digest)
    except (ValueError, TypeError) as error:
        raise ReferenceError("assessment requires an exact product pin") from error


def output_key(value):
    if (
        not isinstance(value, Mapping)
        or set(value) != {"layer", "collection", "local_id"}
        or value["collection"] not in COLLECTIONS
        or not isinstance(value["local_id"], str)
        or not value["local_id"]
    ):
        raise ReferenceError("assessment output requires typed layer/collection/local identity")
    return (*pin_key(value["layer"]), value["collection"], value["local_id"])


def _identity(collection, row):
    return row["family"] if collection == "coverage" else row["local_id"]


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
    pending, visited, retained = deque([graph["root"]]), set(), []
    while pending:
        identity = pending.popleft()
        if identity in visited:
            continue
        visited.add(identity)
        node = nodes[identity]
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
        pending.extend(edge["target"] for edge in edges)
    return dict(root=graph["root"], nodes=retained)


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
        left = {row["id"]: row for row in actual["nodes"]}
        right = {row["id"]: row for row in expected["nodes"]}
        if len(left) != len(actual["nodes"]) or len(right) != len(expected["nodes"]):
            return False
        import networkx as nx
        from networkx.algorithms.isomorphism import MultiDiGraphMatcher

        def as_graph(graph, nodes):
            result = nx.MultiDiGraph()
            for identity, node in nodes.items():
                result.add_node(
                    identity, value=canonical_bytes(node["value"]), root=identity == graph["root"]
                )
            for identity, node in nodes.items():
                for edge in node["edges"]:
                    if edge["target"] not in nodes:
                        raise ReferenceError("graph edge lacks an exact selected target")
                    result.add_edge(
                        identity,
                        edge["target"],
                        meaning=canonical_bytes(
                            {key: value for key, value in edge.items() if key != "target"}
                        ),
                    )
            return result

        x, y = as_graph(actual, left), as_graph(expected, right)
        matcher = MultiDiGraphMatcher(
            x,
            y,
            node_match=lambda a, b: a == b,
            edge_match=lambda a, b: (
                Counter(item["meaning"] for item in a.values())
                == Counter(item["meaning"] for item in b.values())
            ),
        )
        return matcher.is_isomorphic()
    except KeyError, TypeError, ValueError:
        return False


def _matches(actual, expected, graph_projection=None):
    return all(
        graph_equal(actual.get(key), value, graph_projection)
        if key == "graph"
        else key in actual and _subset(actual[key], value)
        for key, value in expected.items()
    )


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
        pin = output["layer"]
        body = self.layer(pin)
        local = (
            "@coverage:" + output["local_id"]
            if output["collection"] == "coverage"
            else output["local_id"]
        )
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
                        edge(name, target["local_id"], target["layer"], position=position)
                elif name == "head" and collection == "named_binding":
                    edge(name, data["local_id"], data["layer"])
                elif name in {"members", "antecedent_members"} and collection == "named_binding":
                    for position, target in enumerate(data):
                        edge(name, target["local_id"], target["layer"], position=position)
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
                            container["local_id"],
                            container["layer"],
                        )
                    for position, target in enumerate(match.pop("nodes", ())):
                        edge(
                            "named_match.nodes",
                            target["local_id"],
                            target["layer"],
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
                                target["local_id"],
                                target["layer"],
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
                                target["local_id"],
                                target["layer"],
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
                dict(layer=current_pin, local_id=identity)
                if isinstance(identity, str)
                else dict(
                    layer=current_pin,
                    local_id=identity[1],
                    path=["named_match", "bindings", identity[2]],
                )
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
                    raise ReferenceError("operation author witness graph exceeds byte bound")
            nodes.append(node)
        return dict(
            root=names[initial],
            roots=[names[(*pin_key(pin), local)] for pin, local in roots],
            nodes=nodes,
        )


_EXTENT_FIELDS = {"source_view_id", "projection", "native_pointer", "start", "end"}


def _scope_relation(row, opportunity):
    """Locate outputs without treating missing coordinates as known outside scope."""
    if row["collection"] == "coverage":
        selectors = (*row["value"].get("eligible", ()), *row["value"].get("examined", ()))

        def contains(selector, extent):
            return (
                selector["projection"] == extent["projection"]
                and selector.get("start", 0) <= extent["start"]
                and selector.get("end", extent["end"]) >= extent["end"]
            )

        if all(
            any(contains(selector, extent) for selector in selectors)
            for extent in opportunity.extents
        ):
            return "inside"
        if any(
            selector["projection"] == extent["projection"]
            and selector.get("start", 0) < extent["end"]
            and selector.get("end", extent["end"]) > extent["start"]
            for selector in selectors
            for extent in opportunity.extents
        ):
            return "crossing"
        return "outside"
    extents = row["extents"]
    if not extents:
        return "unlocated"
    exact = all(set(extent) == _EXTENT_FIELDS for extent in extents)
    if exact:
        if all(
            any(
                extent["source_view_id"] == scope["source_view_id"]
                and extent["projection"] == scope["projection"]
                and extent["native_pointer"] == scope["native_pointer"]
                and scope["start"] <= extent["start"] <= extent["end"] <= scope["end"]
                for scope in opportunity.extents
            )
            for extent in extents
        ):
            return "inside"
        if any(
            extent["source_view_id"] == scope["source_view_id"]
            and extent["projection"] == scope["projection"]
            and extent["native_pointer"] == scope["native_pointer"]
            and extent["start"] < scope["end"]
            and extent["end"] > scope["start"]
            for extent in extents
            for scope in opportunity.extents
        ):
            return "crossing"
        return "outside"
    # Partial identity can prove disjointness, but missing offsets alone cannot.
    if all(
        not any(
            all(
                extent.get(key, scope[key]) == scope[key]
                for key in ("source_view_id", "projection", "native_pointer")
            )
            for scope in opportunity.extents
        )
        for extent in extents
    ):
        return "outside"
    return "unlocated"


_NATIVE_COLUMN_SCHEMES = {
    ("spacy", "spacy-token-columns-1"): {
        "spacy.lemma": "lemma",
        "spacy.pos": "pos",
        "spacy.tag": "tag",
        "spacy.morphology": "morphology",
        "spacy.dependency": "dependency",
    },
    ("hanlp", "hanlp-canonical-token-1"): {
        "hanlp.lemma": "lemma",
        "hanlp.pos": "tag",
        "hanlp.dependency": "dependency",
    },
}


def _native_provider(body, row):
    identity = row.get("native_token", {}).get("native_run")
    return next(
        (run["provider"] for run in body.get("native_runs", ()) if run["local_id"] == identity),
        None,
    )


def _native_column_availability(row):
    value = row["value"]
    provider = row.get("native_provider")
    if value.get("kind") != "native.token" or value.get("family") != f"{provider}.tokens":
        return {}
    columns = _NATIVE_COLUMN_SCHEMES.get((provider, value.get("native_scheme")), {})
    native = value.get("native_token", {})
    availability = {}
    for family, column in columns.items():
        item = native.get(column)
        present = isinstance(item, str) and bool(item)
        if column == "morphology":
            present = isinstance(item, (list, tuple)) and all(
                isinstance(feature, str) for feature in item
            )
        if column == "dependency":
            expected_base = 0 if provider == "spacy" else 1
            present = (
                present
                and type(native.get("native_head")) is int
                and type(native.get("head_index_base")) is int
                and native["head_index_base"] == expected_base
            )
        availability[family] = present
    return availability


def _family_matches(row, family):
    declared = row["value"].get("family")
    if declared == family:
        return True
    if _native_column_availability(row).get(family, False):
        return True
    return declared is None and family in row.get("families", ())


def score_characterization(
    frame, cases, predictions, *, coverage=(), native_scores=None
) -> dict[str, Any]:
    by_opportunity = {o.opportunity_id: o for o in frame.opportunities}
    frozen = {output_key(v) for v in frame.outputs or ()}
    if frame.direction == "output_first" and frozen - {
        output_key(v["reference"]) for v in predictions
    }:
        raise ReferenceError("frozen output population is absent from prediction capture")
    results: list[dict[str, Any]] = []
    for case in cases:
        if case.semantic_reference is not None:
            results.append(_semantic_case_result(frame, case, predictions, coverage))
            continue
        if case.native_reference is not None:
            if native_scores is None or case.case_id not in native_scores:
                from .native_scoring import NativeScoringReference, score_native

                metrics = score_native(
                    None,
                    NativeScoringReference.model_validate_json(
                        canonical_bytes(case.native_reference)
                    ),
                )
            else:
                metrics = native_scores[case.case_id]
            results.append(_native_case_result(frame, case, metrics))
            continue
        opportunity = by_opportunity[case.opportunity_id]
        family = case.required_family
        if not isinstance(family, str) or not family:
            raise ReferenceError("characterization case requires an explicit assessed family")
        relevant = [r for r in coverage if r["family"] == family]
        selected = [
            row
            for row in predictions
            if _family_matches(row, family)
            and _subset(row, case.candidate_selector)
            and (
                case.output_reference is None
                or output_key(row["reference"]) == output_key(case.output_reference)
            )
        ]
        candidates = [
            row
            for row in selected
            if frame.direction == "output_first" or _scope_relation(row, opportunity) == "inside"
        ]
        matches = [
            row
            for row in candidates
            if any(
                _matches(row, alternative, case.graph_projection)
                for alternative in case.alternatives
            )
        ]
        unlocated = [
            row
            for row in selected
            if _scope_relation(row, opportunity) in {"unlocated", "crossing"}
        ]
        coverage_case = case.candidate_selector.get("collection") == "coverage" and bool(candidates)
        native_column_rows = [
            row
            for row in predictions
            if family in _native_column_availability(row)
            and _subset(row, case.candidate_selector)
            and (
                case.output_reference is None
                or output_key(row["reference"]) == output_key(case.output_reference)
            )
            and (
                frame.direction == "output_first" or _scope_relation(row, opportunity) != "outside"
            )
        ]
        missing_columns = [
            row for row in native_column_rows if not _native_column_availability(row)[family]
        ]
        examined = all(
            any(
                r["availability"] == "available"
                and r["outcome"] in {"complete", "empty", "partial"}
                and any(
                    s["projection"] == e["projection"]
                    and s.get("start", 0) <= e["start"]
                    and s.get("end", e["end"]) >= e["end"]
                    for s in r["examined"]
                )
                for r in relevant
            )
            for e in opportunity.extents
        )
        if case.source_state == "inapplicable":
            judgment, category = "unassessed", "inapplicable"
        elif case.judgment == "unassessed" or case.source_state == "uninspected":
            judgment, category = "unassessed", "uninspected"
        elif missing_columns:
            judgment, category = "unassessed", "native_column_unavailable"
        elif native_column_rows and not examined:
            judgment, category = "unassessed", "prediction_scope_unavailable"
        elif frame.direction == "source_first" and (
            unlocated or (not examined and not coverage_case)
        ):
            judgment, category = (
                "unassessed",
                "mapping_unavailable" if unlocated else "prediction_scope_unavailable",
            )
        elif frame.direction == "output_first" and case.judgment == "unsupported":
            judgment, category = "unsupported", case.error_category or "unsupported_output"
        elif case.source_state == "unresolved" or case.judgment == "ambiguous":
            judgment, category = (
                "ambiguous",
                "permissible_alternatives" if matches else "unresolved",
            )
        elif case.expectation_mode == "absence_detection":
            judgment, category = (
                ("unsupported", "spurious_output")
                if candidates
                else ("supported", "inspected_unstated")
            )
        elif case.judgment == "unsupported":
            judgment, category = "unsupported", case.error_category or "unsupported_output"
        elif matches:
            judgment, category = "supported", None
        else:
            judgment, category = (
                "unsupported",
                case.error_category or ("wrong_structure" if candidates else "missed_opportunity"),
            )
        if (
            case.graph_projection == "source_semantics"
            and any("graph" in a for a in case.alternatives)
            and category == "wrong_structure"
        ):
            category = "structural_projection_mismatch"
        results.append(
            dict(
                comparison_contract="legacy_structural_graph"
                if case.graph_projection == "source_semantics"
                else "declared_fields_or_exact_native_graph",
                case_id=case.case_id,
                opportunity_id=case.opportunity_id,
                facet=case.facet,
                judgment=judgment,
                source_state=case.source_state,
                error_category=category,
                candidate_references=[r["reference"] for r in candidates],
                matched_references=[r["reference"] for r in matches],
                explanation=case.explanation,
            )
        )
    by_id = {
        o.opportunity_id: [r for r in results if r["opportunity_id"] == o.opportunity_id]
        for o in frame.opportunities
    }
    source_coverage = dict(
        grain="frozen_source_opportunity",
        opportunity_count=len(frame.opportunities),
        opportunities=[
            dict(
                asdict(o),
                assessments=[
                    dict(
                        case_id=r["case_id"],
                        facet=r["facet"],
                        judgment=r["judgment"],
                        source_state=r["source_state"],
                        error_category=r["error_category"],
                    )
                    for r in by_id[o.opportunity_id]
                ],
                assessment_status="assessed_cases"
                if by_id[o.opportunity_id]
                else "reference_missing",
            )
            for o in frame.opportunities
        ],
    )
    return dict(
        direction=frame.direction,
        grain="characterization_case_facet",
        source_coverage=source_coverage,
        output_coverage=dict(
            grain="frozen_output_identity"
            if frame.direction == "output_first"
            else "source_scoped_prediction",
            selected_count=len(frozen) if frame.direction == "output_first" else len(predictions),
        ),
        family_coverage=list(coverage),
        cases=results,
        facets={
            facet: dict(Counter(r["judgment"] for r in results if r["facet"] == facet))
            for facet in sorted({r["facet"] for r in results})
        },
        quality_claim="not_established",
    )


def _scope_examined(opportunity, family, coverage):
    return all(
        any(
            row["family"] == family
            and row["availability"] == "available"
            and row["outcome"] in {"complete", "empty", "partial"}
            and any(
                selector["projection"] == extent["projection"]
                and selector.get("start", 0) <= extent["start"]
                and selector.get("end", extent["end"]) >= extent["end"]
                for selector in row.get("examined", ())
            )
            for row in coverage
        )
        for extent in opportunity.extents
    )


class NativeCaseInputs:
    """Restore and cache bounded-unit retained Docs, never run a spaCy pipeline."""

    def __init__(self, conn, frame, pins, projection, coverage):
        self.conn, self.frame, self.pins = conn, frame, pins
        self.projection, self.coverage = projection, coverage
        self.views, self.docs = {}, {}
        self.vocab = None

    def score(self, case):
        from types import SimpleNamespace

        from spacy.vocab import Vocab

        from corpus_structure.methods.native_evidence_layers import retained_spacy_docs
        from corpus_structure.semantic.source_views import load_source_view

        from .native_scoring import NativeScoringReference, score_native

        reference = NativeScoringReference.model_validate_json(
            canonical_bytes(case.native_reference)
        )
        opportunity = next(
            o for o in self.frame.opportunities if o.opportunity_id == case.opportunity_id
        )

        def unavailable(reason):
            return dict(score_native(None, reference), reason=reason)

        if not reference.inspected:
            return score_native(None, reference)
        if not _scope_examined(opportunity, case.required_family, self.coverage):
            return unavailable("native_family_scope_unavailable")
        if (
            (reference.kind == "tokenization" and case.required_family != "spacy.tokens")
            or (reference.kind == "dependencies" and case.required_family != "spacy.dependency")
            or (
                reference.kind == "spans"
                and reference.span_key == "sents"
                and case.required_family != "spacy.sentences"
            )
        ):
            return unavailable("native_question_family_incompatible")
        requested = canonical_bytes(opportunity.extents)
        matches = []
        for pin in self.pins:
            body = self.projection.layer(pin)
            if case.required_family not in body["operation"]["produced_families"]:
                continue
            if case.output_reference is not None and pin_key(pin) != pin_key(
                case.output_reference["layer"]
            ):
                continue
            occurrences = {o["local_id"]: o["extents"] for o in body["occurrences"]}
            annotations = {a["local_id"]: a for a in body["annotations"]}
            if case.output_reference is not None and (
                case.output_reference["collection"] != "annotations"
                or annotations.get(case.output_reference["local_id"], {}).get("kind")
                != "native.block"
            ):
                return unavailable("native_output_reference_incompatible")
            containers = {
                a["native_token"]["container"]
                for a in annotations.values()
                if a.get("native_token", {}).get("native_run") == "spacy"
            }
            for container in containers:
                if case.output_reference is not None and (
                    case.output_reference["collection"] != "annotations"
                    or case.output_reference["local_id"] != container
                ):
                    continue
                block = annotations.get(container)
                if block is None:
                    continue
                extents = [
                    extent
                    for oid in block.get("occurrences", ())
                    for extent in occurrences[oid]
                    if not extent.get("synthetic", False)
                ]
                if not extents or any(not set(extent) >= _EXTENT_FIELDS for extent in extents):
                    continue
                signature = [{key: extent[key] for key in _EXTENT_FIELDS} for extent in extents]
                if canonical_bytes(signature) == requested:
                    matches.append((pin, container, body))
        if len(matches) != 1:
            return unavailable(
                "native_block_scope_ambiguous" if matches else "native_block_scope_unavailable"
            )
        pin, container, body = matches[0]
        required = ("dependency",) if reference.kind == "dependencies" else ()
        key = (pin_key(pin), required)
        if key not in self.docs:
            for identity in body["source_scope"]["source_view_ids"]:
                if identity not in self.views:
                    self.views[identity] = load_source_view(self.conn, identity, analysis=False)
            if self.vocab is None:
                self.vocab = Vocab()
            try:
                self.docs[key] = retained_spacy_docs(
                    SimpleNamespace(payload=body), self.views, self.vocab, required=required
                )
            except ValueError, KeyError, TypeError:
                self.docs[key] = None
        restored = self.docs[key]
        if restored is None:
            return unavailable("native_retained_restoration_unavailable")
        result = score_native(restored.get(container), reference)
        result["prediction_reference"] = dict(
            layer=pin, collection="annotations", local_id=container
        )
        result["source_scope"] = [dict(e) for e in opportunity.extents]
        return result


def _native_case_result(frame, case, metrics):
    if case.source_state == "inapplicable":
        judgment, category = "unassessed", "inapplicable"
    elif case.judgment == "unassessed" or case.source_state == "uninspected":
        judgment, category = "unassessed", "uninspected"
    elif frame.direction == "output_first" and case.judgment == "unsupported":
        judgment, category = "unsupported", case.error_category or "unsupported_output"
    elif metrics["status"] != "scored" or type(metrics.get("exact_match")) is not bool:
        judgment, category = "unassessed", metrics.get("reason") or "native_scope_unavailable"
    elif case.source_state == "unresolved" or case.judgment == "ambiguous":
        judgment, category = "ambiguous", "unresolved"
    elif metrics["exact_match"]:
        judgment, category = "supported", None
    else:
        judgment, category = "unsupported", case.error_category or "wrong_native_structure"
    reference = metrics.get("prediction_reference")
    return dict(
        case_id=case.case_id,
        opportunity_id=case.opportunity_id,
        facet=case.facet,
        judgment=judgment,
        source_state=case.source_state,
        error_category=category,
        candidate_references=[reference] if reference is not None else [],
        matched_references=[reference] if reference is not None and judgment == "supported" else [],
        native_metrics=metrics,
        explanation=case.explanation,
    )


def _semantic_case_result(frame, case, predictions, coverage):
    from .task_semantics import score_task

    opportunity = next(o for o in frame.opportunities if o.opportunity_id == case.opportunity_id)
    selected = [
        row
        for row in predictions
        if _family_matches(row, case.required_family)
        and (
            case.output_reference is None
            or output_key(row["reference"]) == output_key(case.output_reference)
        )
    ]
    metrics = score_task(
        case.semantic_reference,
        case.required_family,
        selected,
        output_first=frame.direction == "output_first",
    )
    if case.source_state == "inapplicable":
        judgment, category = "unassessed", "inapplicable"
    elif case.judgment == "unassessed" or case.source_state == "uninspected":
        judgment, category = "unassessed", "uninspected"
    elif not _scope_examined(opportunity, case.required_family, coverage):
        judgment, category = "unassessed", "prediction_scope_unavailable"
    elif metrics["status"] != "scored":
        judgment, category = (
            "unassessed",
            "witness_support_unknown"
            if metrics.get("reason") == "witness_support_unknown"
            else "assessment_contract_unavailable",
        )
    elif frame.direction == "output_first" and case.judgment == "unsupported":
        judgment, category = "unsupported", case.error_category or "unsupported_output"
    elif case.source_state == "unresolved" or case.judgment == "ambiguous":
        judgment, category = (
            "ambiguous",
            "permissible_alternatives" if metrics["exact_match"] else "unresolved",
        )
    else:
        judgment, category = (
            ("supported", None)
            if metrics["exact_match"]
            else ("unsupported", "wrong_task_structure" if selected else "missed_opportunity")
        )
    return dict(
        case_id=case.case_id,
        opportunity_id=case.opportunity_id,
        facet=case.facet,
        judgment=judgment,
        source_state=case.source_state,
        error_category=category,
        candidate_references=[row["reference"] for row in selected],
        semantic_metrics=metrics,
        explanation=case.explanation,
    )


def evaluate_characterization(
    conn,
    *,
    project_id,
    run_id,
    set_id,
    completed,
    prepared,
    definition,
    units,
    frames,
    characterization_view,
):
    from corpus_structure.semantic.characterization_store import (
        read_layer,
        read_layer_manifest,
        read_view,
    )

    from .operation_assessment import EVALUATION_PROTOCOL, _call, _json, read_pass, source_units
    from .semantic import ReferenceReport

    run_views = {u["source_view_id"] for u in source_units(conn, run_id)}
    if {u["source_view_id"] for u in units} - run_views:
        raise ReferenceError("characterization evaluation lacks frozen source views")
    snapshot = _call(conn, "SELECT eval.native_reference_snapshot(:s)", s=set_id).scalar_one()
    if not units or len(snapshot) != len(units):
        raise ReferenceError("every characterization unit requires adjudicated C")
    frozen = {r["unit_id"]: r for r in snapshot}
    reports = []
    for unit in units:
        frame = frames[unit["unit_key"]]
        pin = (
            frame.characterization_view
            if frame.direction == "output_first"
            else characterization_view
        )
        if pin is None:
            raise ReferenceError(
                "source-first grading requires an independently selected characterization view"
            )
        if (
            frame.direction == "output_first"
            and characterization_view is not None
            and pin_key(characterization_view) != pin_key(pin)
        ):
            raise ReferenceError("output-first grading cannot override its frozen view")
        view = read_view(conn, ProductReference(**pin), run_id=run_id).payload
        active = view.get("active_layers", view["layers"])
        if frame.direction == "output_first" and {pin_key(p) for p in frame.selected_layers} - {
            pin_key(p) for p in active
        }:
            raise ReferenceError("output frame adopts dependency-only evidence")
        selected_pins = frame.selected_layers if frame.direction == "output_first" else active
        frame_views = {e["source_view_id"] for o in frame.opportunities for e in o.extents}
        all_selected = list(selected_pins)
        selected_pins = [
            p
            for p in selected_pins
            if frame_views
            & set(
                read_layer_manifest(conn, ProductReference(**p), run_id=run_id).payload[
                    "source_scope"
                ]["source_view_ids"]
            )
        ]
        if frame.direction == "output_first" and len(selected_pins) != len(all_selected):
            raise ReferenceError("output-first layer scope is outside frozen source views")
        projection = LayerProjection(
            lambda p: read_layer(conn, ProductReference(**p), run_id=run_id).payload
        )
        reference = read_pass(
            conn, frozen[unit["id"]]["pass_id"], frame_id=frozen[unit["id"]]["frame_id"]
        )
        cases = reference["payload"]["cases"]
        ordinary_cases = [case for case in cases if case.native_reference is None]
        coverage, predictions = [], []
        for layer_pin in selected_pins:
            body = projection.layer(layer_pin)
            if not {e["source_view_id"] for o in frame.opportunities for e in o.extents} & set(
                body["source_scope"]["source_view_ids"]
            ):
                continue
            coverage.extend(body["coverage"])
            if frame.direction == "output_first":
                outputs = [o for o in frame.outputs if pin_key(o["layer"]) == pin_key(layer_pin)]
            else:
                outputs = [
                    dict(layer=layer_pin, collection=name, local_id=_identity(name, value))
                    for name in COLLECTIONS
                    for value in body.get(name, ())
                ]
            for output in outputs:
                if frame.direction == "source_first":
                    local = (
                        "@coverage:" + output["local_id"]
                        if output["collection"] == "coverage"
                        else output["local_id"]
                    )
                    collection, row = projection.indexes[pin_key(layer_pin)][local]
                    # Select by rubric fields before constructing the rooted graph. Rows
                    # without complete coordinates remain diagnostics for relevant cases.
                    metadata = dict(
                        collection=collection,
                        value=row,
                        native_provider=_native_provider(body, row),
                        families=[row["family"]]
                        if "family" in row
                        else [item["family"] for item in body["coverage"]],
                    )
                    if not any(
                        (
                            _family_matches(metadata, case.required_family)
                            or _native_column_availability(metadata).get(case.required_family)
                            is False
                        )
                        and _subset(metadata, case.candidate_selector)
                        for case in ordinary_cases
                    ):
                        continue
                projected = projection.project(output, include_graph=False)
                if (
                    frame.direction == "source_first"
                    and all(
                        _scope_relation(projected, opportunity) == "outside"
                        for opportunity in frame.opportunities
                    )
                    and not any(
                        case.semantic_reference is not None
                        and _family_matches(projected, case.required_family)
                        for case in ordinary_cases
                    )
                ):
                    continue
                needs_legacy_graph = any(
                    case.semantic_reference is None
                    and any("graph" in a for a in case.alternatives)
                    and _family_matches(projected, case.required_family)
                    and _subset(projected, case.candidate_selector)
                    for case in ordinary_cases
                )
                if needs_legacy_graph:
                    local = (
                        "@coverage:" + output["local_id"]
                        if output["collection"] == "coverage"
                        else output["local_id"]
                    )
                    projected["graph"] = projection.graph(output["layer"], local)
                predictions.append(projected)
        task_families = {
            case.required_family for case in ordinary_cases if case.semantic_reference is not None
        }
        for family in task_families:
            population = [row for row in predictions if _family_matches(row, family)]
            roots = [
                (
                    row["reference"]["layer"],
                    "@coverage:" + row["reference"]["local_id"]
                    if row["collection"] == "coverage"
                    else row["reference"]["local_id"],
                )
                for row in population
            ]
            shared = projection.graph_many(roots, witness_closure=True)
            for row, root in zip(population, shared["roots"], strict=True):
                row["task_graph"] = shared
                row["task_graph_root"] = root
        inputs = NativeCaseInputs(conn, frame, selected_pins, projection, coverage)
        native_scores = {
            case.case_id: inputs.score(case) for case in cases if case.native_reference is not None
        }
        report = score_characterization(
            frame, cases, predictions, coverage=coverage, native_scores=native_scores
        )
        reports.append(
            dict(
                report,
                unit_id=unit["id"],
                source_view_id=unit["source_view_id"],
                characterization_view=pin,
                selected_layers=list(selected_pins),
            )
        )
    result = dict(
        protocol=EVALUATION_PROTOCOL,
        set_id=set_id,
        run_id=run_id,
        release_id=prepared.release_id,
        reference_snapshot=snapshot,
        units=reports,
        partition=definition["sampling"]["partition"],
        frame_digest=sha256(canonical_bytes([unit["context"] for unit in units])).hexdigest(),
        quality_claim="not_established",
        population_claim="declared_cases_only",
    )
    identity = _call(
        conn,
        "SELECT eval.record_operation_reference_evaluation("
        ":p,:r,:s,CAST(:n AS jsonb),CAST(:v AS jsonb))",
        p=project_id,
        r=run_id,
        s=set_id,
        n=_json(snapshot),
        v=_json(result),
    ).scalar_one()
    return ReferenceReport(
        id=identity,
        project_id=project_id,
        run_id=run_id,
        set_id=set_id,
        reference_snapshot=snapshot,
        result=result,
    )
