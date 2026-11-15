"""Bounded transport-neutral interpretation lookup and retained review detail."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict

from corpus_structure.semantic.data_operation_json import DdoJsonValue, json_bytes
from corpus_structure.semantic.demand_queries import DemandQueryRequest, serve_demand_query
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
