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
    ASSESSMENT_NATIVE_COLLECTIONS,
    ASSESSMENT_NODE_KINDS,
    ASSESSMENT_RELATION_KINDS,
)
from corpus_structure.semantic.identity import canonical_bytes
from corpus_structure.semantic.refusal_types import ReferenceError


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
    **{
        kind: {"collection", "record_type", "block_id", "ordinal", "start", "end"}
        for kind in ASSESSMENT_NATIVE_COLLECTIONS
    },
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


class SelectedAnnotationTargets:
    """Resolve annotation evidence against one acquired graph cut's producing inputs."""

    def __init__(self, index, cut):
        from corpus_structure.semantic.detached_reference_resolution import IndexedReferenceAccess

        self.index = index
        self.demand_id = cut.record["demand_id"]
        self.access = IndexedReferenceAccess(
            lambda relation, *keys: index.mapping(relation, keys),
            cut.record["project_id"],
            population_archive=getattr(index, "population_archive", None),
        )
        self.producers = {}

    def __call__(self, owner, reference):
        from corpus_structure.semantic.reference_resolution import (
            ProducingReferenceBindings,
            ProducingReferenceInput,
            ReferenceResolver,
            ReferenceTarget,
        )

        product_id = owner["product_id"]
        if product_id not in self.producers:
            output_episodes = {
                row["derivation_id"]
                for row in self.index.rows_for("ops.data_derivation_output", product_id=product_id)
                if row["role"] == "result"
            }
            selected = {
                episode
                for episode in output_episodes
                if next(
                    self.index.rows_for(
                        "ops.demand_use",
                        demand_id=self.demand_id,
                        fate="fulfilled",
                        derivation_id=episode,
                    ),
                    None,
                )
                is not None
            }
            if len(selected) != 1:
                raise ReferenceError(
                    "annotation witness requires one exact selected producing derivation"
                )
            (episode,) = selected
            bindings = []
            for row in self.index.rows_for(
                "ops.data_derivation_input", derivation_id=episode, role="sentences"
            ):
                parent = self.access.products.get(row["product_id"])
                if parent is None or row.get("member_id") is not None:
                    raise ReferenceError(
                        "annotation witness requires the selected whole population"
                    )
                contract = parent["kind_contract"]
                kind = self.access.kinds.get(contract)
                if kind is None or kind["kind"] != (
                    "https://corpus-structure.dev/semantic/data-operation-sentences/DdoSourceAnnotations"
                ):
                    raise ReferenceError("annotation witness has another nominal input population")
                bindings.append(
                    ProducingReferenceInput(
                        "sentences", row["product_id"], contract, multiplicity=row["multiplicity"]
                    )
                )
            if len(bindings) != 1:
                raise ReferenceError(
                    "annotation witness requires one exact selected input population"
                )
            (binding,) = bindings
            original = ProducingReferenceBindings(episode, tuple(bindings))
            root = self.access.product(product_id)
            self.access.authorize(binding)
            native = self.access.product(binding.product_id)
            if any(root[field] != native[field] for field in ("source", "selectors")):
                raise ReferenceError("annotation witness changes original source or analyzed scope")
            self.producers[product_id] = ReferenceResolver(original, self.access), binding
        resolver, binding = self.producers[product_id]
        try:
            row = resolver.resolve(
                reference,
                ReferenceTarget("sentences", "partition-item", binding.kind_contract, "rows"),
            )
            packet = self.access.partition_header(
                binding.product_id, reference.collection, reference.partition_key
            )
        except (KeyError, ValueError) as error:
            raise ReferenceError(
                "annotation witness is outside the exact selected partition"
            ) from error
        return (
            {"product_id": binding.product_id},
            dict(packet["placement"], ordinal=packet["ordinal"]),
            row,
        )


class LayerProjection:
    def __init__(self, load, annotation_targets=None):
        self.load = load
        self.annotation_targets = annotation_targets
        self.annotation_support = {}
        self.layers = {}
        self.indexes = {}
        self.choice_groups = {}

    def layer(self, pin):
        key = pin_key(pin)
        if key not in self.layers:
            try:
                body = self.load(pin)
            except KeyError as error:
                raise ReferenceError(
                    "graph witness product is absent from selected closure"
                ) from error
            self.layers[key] = body
            if body.get("annotation_support"):
                from corpus_structure.semantic.construction_products import annotation_support_index

                self.annotation_support[key] = annotation_support_index(body)
            else:
                self.annotation_support[key] = {}
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
            self.indexes[key] = index
        return self.layers[key]

    def annotation_item(self, owner, reference):
        if self.annotation_targets is None:
            raise ReferenceError("annotation witness requires an authenticated producing cut")
        pin, placement, row = self.annotation_targets(owner, reference)
        self.layer(pin)
        collection = "native_" + row["record_type"]
        key = ("partition-item", reference.collection, reference.partition_key, reference.item_key)
        payload = {
            **row,
            "record_type": collection,
            "block_id": reference.partition_key,
            "start": placement["start"] + row["start"],
            "end": placement["start"] + row["end"],
        }
        block = ("partition", reference.collection, reference.partition_key)
        index = self.indexes[pin_key(pin)]
        index[key] = collection, payload
        index[block] = (
            "native_block",
            dict(record_type="native_block", block_id=reference.partition_key, **placement),
        )
        return pin, key, block

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
            families=[row["family"]]
            if "family" in row
            else [item["family"] for item in body.get("coverage", ())],
            extents=[
                {k: e[k] for k in ("projection", "native_pointer", "start", "end") if k in e}
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

            supports = self.annotation_support[key]

            def native_edges(
                label,
                use,
                owner,
                binding=None,
                *,
                block_id=None,
                supports=supports,
                current_pin=current_pin,
                edge=edge,
            ):
                references = supports.get((owner, use, binding), ())
                locations = []
                for position, reference in references:
                    if block_id is not None and reference.partition_key != block_id:
                        raise ReferenceError("annotation witness leaves its exact named block")
                    target_pin, item, block = self.annotation_item(current_pin, reference)
                    fields = {} if label == "head" else {"position": position}
                    edge(label, item, target_pin, **fields)
                    locations.append((target_pin, block))
                return locations

            def external_edges(
                label,
                data,
                use=None,
                *,
                supports=supports,
                identity=identity,
                current_pin=current_pin,
                edge=edge,
            ):
                native = dict(supports.get((identity, use, None), ())) if use else {}
                if native and max(native) >= len(data) + len(native):
                    raise ReferenceError(
                        "annotation witness position exceeds the original premise list"
                    )
                retained = iter(data)
                for position in range(len(data) + len(native)):
                    if position in native:
                        target_pin, item, _ = self.annotation_item(current_pin, native[position])
                        edge(label, item, target_pin, position=position)
                    else:
                        target_pin, target = _graph_member(next(retained))
                        edge(label, target, target_pin, position=position)

            if collection == "named_binding":
                _, owner, binding = identity
                block_id = self.indexes[key][owner][1]["named_match"]["block_id"]
                if not native_edges(
                    "head", "named_binding_head", owner, binding, block_id=block_id
                ):
                    raise ReferenceError("named binding lacks its exact native head")
                native_edges("members", "named_binding_member", owner, binding, block_id=block_id)
                native_edges(
                    "antecedent_members",
                    "named_binding_antecedent",
                    owner,
                    binding,
                    block_id=block_id,
                )
            if "external_premises" in row or (identity, "external_premise", None) in supports:
                external_edges(
                    "external_premises", row.get("external_premises", ()), "external_premise"
                )

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
                elif name == "external_premises":
                    continue
                elif name == "required_external_choices":
                    external_edges(name, data)
                elif name in {"native_token", "native_mention", "native_edu"} and witness_closure:
                    detail = dict(data)
                    for field in ("container", "sentence"):
                        target = detail.pop(field, None)
                        if target is not None:
                            edge(name + "." + field, target)
                    value[name] = detail
                elif name == "named_match":
                    match = dict(data)
                    block_id = match.pop("block_id")
                    locations = native_edges(
                        "named_match.nodes", "named_node", identity, block_id=block_id
                    )
                    if not locations:
                        raise ReferenceError("named witness lacks its actual annotation partition")
                    native_pin, block = locations[0]
                    edge("named_match.native_container", block, native_pin)
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
                        tokens = detail["native_tokens"]
                        references = supports.get((identity, "navigation_token", None), ())
                        if tuple(position for position, _ in references) != tuple(
                            range(len(tokens))
                        ):
                            raise ReferenceError("navigation has incomplete native token evidence")
                        for position, reference in references:
                            target_pin, item, _ = self.annotation_item(current_pin, reference)
                            edge(
                                "navigation.native_tokens.native_node",
                                item,
                                target_pin,
                                position=position,
                                **tokens[position],
                            )
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
                    external_edges(
                        "basis.external_premises",
                        basis.pop("external_premises", ()),
                        "basis_external_premise",
                    )
                    external_edges(
                        "basis.required_external_choices",
                        basis.pop("required_external_choices", ()),
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
            if isinstance(identity, str):
                qualified = dict(product_id=current_pin["product_id"], member_id=identity)
            elif identity[0] == "named_binding":
                qualified = dict(
                    product_id=current_pin["product_id"],
                    member_id=identity[1],
                    path=["named_match", "bindings", identity[2]],
                )
            else:
                qualified = dict(
                    product_id=current_pin["product_id"],
                    collection=identity[1],
                    partition_key=identity[2],
                )
                if identity[0] == "partition-item":
                    qualified["item_key"] = list(identity[3])
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


_EXTENT_FIELDS = {"projection", "native_pointer", "start", "end"}
