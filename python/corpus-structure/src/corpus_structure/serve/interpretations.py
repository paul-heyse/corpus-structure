"""Bounded transport-neutral interpretation lookup and retained review detail."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict

from corpus_structure.semantic.data_operation_json import DdoJsonValue, json_bytes
from corpus_structure.semantic.demand_queries import DemandQueryRequest, serve_demand_query
from corpus_structure.semantic.grouped_record_interpretations import GroupedInterpretationRequest
from corpus_structure.semantic.releases import open_release


class InterpretationAnswer(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    version: str = "source-interpretation-1"
    kind: str
    body: dict[str, DdoJsonValue]


def answer(kind, body, max_bytes=1024**2):
    from corpus_structure.semantic.refusals import ReadLimit

    report = InterpretationAnswer(kind=kind, body=body)
    content = json_bytes(report.model_dump(mode="python"))
    if len(content) > max_bytes:
        raise ReadLimit("interpretation response exceeds byte budget", reason="oversized_item")
    return report


def term_lookup(conn, *, release_id, field, query=None, browse=False, max_bytes=1024**2):
    from corpus_structure.semantic.interpretations import lookup_terms

    return answer(
        "terminology_lookup",
        lookup_terms(open_release(conn, release_id), field, query, browse=browse),
        max_bytes,
    )


class SelectedProposalRequest(DemandQueryRequest):
    """A genuine selected private proposal member, never an integer review alias."""

    view: Literal["members"] = "members"
    containers_only: Literal[False] = False


def inspect_selected_proposals(connection, request: SelectedProposalRequest):
    """Inspect actual captured private proposal kinds without granting accepted standing.

    Grouped measurement interpretation is not supplied by this selected member view.
    Native purpose and authority-leaf controls remain the only disclosure authority.
    """
    from corpus_structure.semantic.data_operation_admission import bound_data_operation_model

    result = serve_demand_query(connection, request)
    prepared = open_release(connection, result["cut"]["release_id"])
    contracts = {
        identity.owner: identity.key
        for identity in bound_data_operation_model(prepared).identities
        if identity.domain == "kind"
    }
    kinds = {
        contracts[definition.iri]: definition.name
        for definition in prepared.index.definitions.values()
        if definition.iri in contracts and "DdoRichProposalValue" in definition.ancestors
    }
    if request.kind_contract is not None and request.kind_contract not in kinds:
        raise ValueError("selected contract is not a captured private proposal member kind")
    items = []
    for row in result["items"]:
        nominal = kinds.get(row["kind_contract"])
        if nominal is None:
            continue
        checked = prepared.validate_json(nominal, json_bytes(row["body"])).model_dump(
            mode="python", exclude_unset=True
        )
        if checked["standing"] != "private_proposed":
            raise ValueError("selected proposal cannot assert accepted standing")
        items.append({**row, "body": checked})
    return answer(
        "selected_private_proposals",
        {
            **result,
            "items": items,
            "knowledge": "observed" if items else "unknown",
            "capability": "selected_private_proposal_members" if kinds else "unavailable",
        },
        request.max_bytes,
    )


def group_selected_interpretations(connection, request: GroupedInterpretationRequest) -> InterpretationAnswer:
    """Read complete occurrence groups from exact selected candidate universes."""
    from corpus_structure._query_custody import (
        GROUPED_INTERPRETATION_SOURCES,
        SourceCustodyError,
    )
    from corpus_structure.serve.rich_queries import installed_read_implementation

    try:
        with installed_read_implementation(
            type(request), sources=GROUPED_INTERPRETATION_SOURCES,
            profile="grouped-source-records-1",
        ) as implementation:
            return _group_selected_interpretations(connection, request, implementation)
    except SourceCustodyError as error:
        raise ValueError(str(error)) from error


def _group_selected_interpretations(connection, request, implementation):
    import base64
    from hashlib import sha256

    from corpus_structure.semantic.data_operation_json import json_loads
    from corpus_structure.semantic.grouped_record_interpretations import (
        attach_finite_interpretations,
        grouped_candidate_product,
    )
    from corpus_structure.semantic.refusals import ReadLimit
    from corpus_structure.serve.selected_contributions import (
        actual_graph_inputs,
        selected_contribution_scope,
    )

    if request.implementation is not None and request.implementation != implementation:
        raise ValueError("grouped interpretation resource differs from actual installed meaning")
    selection = request.selection()
    digest = sha256(json_bytes(selection)).hexdigest()
    cursor = None
    if request.cursor is not None:
        try:
            cursor = json_loads(base64.b64decode(request.cursor, altchars=b"-_", validate=True))
        except (ValueError, TypeError) as error:
            raise ValueError("invalid grouped interpretation cursor") from error
        if (not isinstance(cursor, dict) or set(cursor) != {"version", "implementation", "selection", "read_id", "cut_id", "offset"} or cursor["version"] != "grouped-source-records-1" or cursor["implementation"] != implementation or cursor["selection"] != digest or type(cursor["offset"]) is not int or cursor["offset"] < 0):
            raise ValueError("cursor differs from the exact grouped interpretation selection")
    if cursor is not None and request.read_id is not None and (
        request.read_id, request.expected_cut
    ) != (cursor["read_id"], cursor["cut_id"]):
        raise ValueError("grouped interpretation cursor differs from explicit native read")
    acquired = request if cursor is None else request.model_copy(update={"read_id": cursor["read_id"], "expected_cut": cursor["cut_id"]})
    roots = {}
    for root in request.roots:
        roots.setdefault(root.product_id, []).append(root)
    with selected_contribution_scope(connection, acquired, product_ids=tuple(roots)) as selected:
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
            definition = next((value for value in selected.prepared.definitions if value.iri == product.nominal), None)
            if definition is not None and (definition.name == "DdoFiniteInterpretationProduct" or "DdoFiniteInterpretationProduct" in definition.ancestors):
                if any(root.member_id is not None or root.interpretation_id is not None for root in roots[identity]):
                    raise ValueError("finite root selects its complete product; occurrence selectors belong to the candidate root")
                finite.append(product)
                continue
            universes[json_bytes(product.reference.model_dump(mode="python"))] = {
                "reference": product.reference.model_dump(mode="python"),
                "context": product.context.record,
                "source_pin": product.body["source_pin"],
                "inspection_outcome": product.body["inspection_outcome"],
                "coverage": product.body["coverage"],
            }
            for group in grouped_candidate_product(selected.prepared, selected.model, product, roots[identity]):
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
            if len(inputs) != 1 or inputs[0].get("member_id") is not None or inputs[0]["product_id"] not in candidate_product_ids:
                raise ValueError("finite root requires its exact selected whole candidate input")
            candidate_id = inputs[0]["product_id"]
            references, _ = actual_graph_inputs(selected.index, product.derivation_id, cut=selected.cut, max_support_edges=request.max_support_edges)
            if not any(reference.product_id == candidate_id and reference.member_id is None for reference in references):
                raise ValueError("finite candidate universe lacks authentic input support")
            grouped = attach_finite_interpretations(selected.prepared, product, grouped, candidate_product_id=candidate_id)
            finite_universes.append({
                "reference": product.reference.model_dump(mode="python"),
                "context": product.context.record,
                "candidate_product_id": candidate_id,
                "mode": product.body["mode"],
                "source_pin": product.body["source_pin"],
            })
        items = [group.model_dump(mode="python") for group in grouped]
        cut_id, cut = selected.cut.identity, selected.cut.record
        obligations = tuple(selected.index.frontier_rows("obligations"))
    offset = 0 if cursor is None else cursor["offset"]
    if offset > len(items):
        raise ValueError("grouped cursor exceeds its pinned population")

    def report(end):
        continuation = None
        if end < len(items):
            continuation = base64.urlsafe_b64encode(json_bytes({
                "version": "grouped-source-records-1", "implementation": implementation, "selection": digest,
                "read_id": cut["read_id"], "cut_id": cut_id, "offset": end,
            })).decode()
        return {
            "version": "grouped-source-records-1", "implementation": implementation, "cut_id": cut_id, "cut": cut,
            "selection": selection, "candidate_universes": list(universes.values()),
            "finite_universes": finite_universes,
            "items": items[offset:end], "continuation": continuation,
            "page_complete": continuation is None,
            "examined_groups": len(items), "obligations": obligations,
            "knowledge": "observed" if items[offset:end] else "unknown",
            "capability": "complete_private_source_record_groups",
            "unavailable_capabilities": ["authored_measurement_and_terminology_judgments", "accepted_knowledge"],
        }

    end = offset
    while end < min(len(items), offset + request.limit):
        trial = answer("grouped_source_record_interpretations", report(end + 1), max_bytes=67108864)
        if len(json_bytes(trial.model_dump(mode="python"))) > request.max_bytes:
            if end == offset:
                raise ReadLimit("one complete interpretation group and its envelope exceed max_bytes", reason="oversized_item")
            break
        end += 1
    return answer("grouped_source_record_interpretations", report(end), request.max_bytes)
