"""Deterministic complete interpretation grouping over acquired selected inputs."""

from .authored_interpretations import JUDGMENT_KINDS, attach_authored_judgment
from .data_operation_json import json_bytes
from .grouped_record_interpretations import attach_finite_interpretations, grouped_candidate_product
from .selected_contribution_input import actual_graph_inputs


def grouped_interpretation_rows(selected, request, authored_judgments):
    roots = {}
    for root in request.roots:
        roots.setdefault(root.product_id, []).append(root)
    groups, found, universes, finite = {}, set(), {}, []
    for product in selected.products():
        identity = product.reference.product_id
        if identity not in roots:
            continue
        # A whole selected product authenticates its complete member population.
        # A member-only native output cannot silently claim whole-report selection.
        if product.reference.member_id is not None:
            continue
        found.add(identity)
        definition = next(
            (value for value in selected.prepared.definitions if value.iri == product.nominal),
            None,
        )
        if definition is not None and (
            definition.name == "DdoFiniteInterpretationProduct"
            or "DdoFiniteInterpretationProduct" in definition.ancestors
        ):
            if any(
                root.member_id is not None or root.interpretation_id is not None
                for root in roots[identity]
            ):
                raise ValueError(
                    "finite root selects its complete product; occurrence selectors belong to the candidate root"
                )
            finite.append(product)
            continue
        universes[json_bytes(product.reference.model_dump(mode="python"))] = {
            "reference": product.reference.model_dump(mode="python"),
            "context": product.context.record,
            "source_pin": product.body["source_pin"],
            "inspection_outcome": product.body["inspection_outcome"],
            "coverage": product.body["coverage"],
        }
        for group in grouped_candidate_product(
            selected.prepared, selected.model, product, roots[identity]
        ):
            groups[group.identity] = group
    if set(roots) != found:
        raise ValueError("interpretation roots require exact selected whole candidate products")
    grouped = tuple(groups[key] for key in sorted(groups))
    candidate_product_ids = set(roots) - {value.reference.product_id for value in finite}
    finite_universes = []
    for product in finite:
        # Input role membership is authenticated native binding, not matching IDs
        # found by recursively searching the result payload.
        episodes = selected.index.mapping("ops.data_derivation", ("id",))
        requests = selected.index.mapping("ops.data_request", ("id",))
        binding = requests[episodes[product.derivation_id]["request_id"]]["binding"]
        inputs = [value for value in binding["inputs"] if value["role"] == "candidates"]
        if (
            len(inputs) != 1
            or inputs[0].get("member_id") is not None
            or inputs[0]["product_id"] not in candidate_product_ids
        ):
            raise ValueError("finite root requires its exact selected whole candidate input")
        candidate_id = inputs[0]["product_id"]
        references, _ = actual_graph_inputs(
            selected.index,
            product.derivation_id,
            cut=selected.cut,
            max_support_edges=request.max_support_edges,
        )
        if not any(
            reference.product_id == candidate_id and reference.member_id is None
            for reference in references
        ):
            raise ValueError("finite candidate universe lacks authentic input support")
        grouped = attach_finite_interpretations(
            selected.prepared, product, grouped, candidate_product_id=candidate_id
        )
        finite_universes.append(
            {
                "reference": product.reference.model_dump(mode="python"),
                "context": product.context.record,
                "candidate_product_id": candidate_id,
                "mode": product.body["mode"],
                "source_pin": product.body["source_pin"],
            }
        )
    for body, provenance in authored_judgments:
        grouped = attach_authored_judgment(grouped, body, **provenance)

    definitions = {value.iri: value.name for value in selected.prepared.definitions}
    judgment_contracts = {
        definitions[value.owner]: value.key
        for value in selected.model.identities
        if value.domain == "kind" and definitions.get(value.owner) in JUDGMENT_KINDS
    }
    items = [group.model_dump(mode="python") for group in grouped]
    metadata = dict(
        universes=list(universes.values()),
        finite_universes=finite_universes,
        judgment_contracts=judgment_contracts,
    )
    return items, metadata
