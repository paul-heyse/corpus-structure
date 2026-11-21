"""Selected member scope is independent of semantic endpoint association.

Controlled native pages test the current reader projection, not native acquisition.
"""

from decimal import Decimal

from corpus_structure.semantic.contribution_queries import read_demand_contributions
from corpus_structure.semantic.data_operation_json import json_bytes
from corpus_structure.semantic.demand_queries import DemandQueryRequest
from corpus_structure.semantic.demand_results import DemandResult
from semantic.demand_result_support import demand_result_page


def test_member_selection_does_not_expand_to_incoming_or_outgoing_endpoints(monkeypatch):
    selected = []

    def read(connection, demand_id, *, project_id, **kwargs):
        selected.append((demand_id, project_id, kwargs))
        return DemandResult(json_bytes(demand_result_page()))

    monkeypatch.setattr("corpus_structure.semantic.demand_queries.read_demand_result", read)
    request = DemandQueryRequest(
        project_id="project:A", demand_id="demand:A", product_id="product:A", member_id="first"
    )
    occurrence = read_demand_contributions(None, request)
    assert [row["member_id"] for row in occurrence["items"]] == ["first"]
    assert occurrence["items"][0]["body"] == {"amount": Decimal("12.340")}
    relation = read_demand_contributions(None, request.model_copy(update={"member_id": "second"}))
    assert [row["member_id"] for row in relation["items"]] == ["second"]
    assert relation["items"][0]["body"] == {"target": "first", "direction": "outgoing"}
    assert relation["items"][0]["derivation_id"] == "episode:original"
    assert relation["cut_id"] == occurrence["cut_id"]
    assert relation["uses"] == occurrence["uses"]
    assert len(selected) == 4
    assert all(entry[2]["scope"] == {"product_ids": ["product:A"]} for entry in selected)
