"""Selected native custody is computational provenance, not scientific endorsement."""

from corpus_structure.semantic.data_operation_json import json_bytes
from corpus_structure.semantic.demand_queries import DemandQueryRequest, serve_demand_query
from corpus_structure.semantic.demand_results import DemandResult
from semantic.demand_result_support import demand_result_page


def test_support_keeps_real_relations_and_unknown_scientific_standing(monkeypatch):
    records = [
        {
            "key": "episode:original",
            "relation": "ops.data_derivation",
            "record": {"id": "episode:original", "state": "published"},
        },
        {
            "key": "input:source",
            "relation": "ops.data_derivation_input",
            "record": {"derivation_id": "episode:original", "product_id": "product:source"},
        },
        {
            "key": "source:A",
            "relation": "ops.original_source_admission",
            "record": {"original_source": "source:A", "digest": "actual-retained-digest"},
        },
    ]
    native = demand_result_page()
    native["view"] = "support"
    for product in native["uses"][0]["products"]:
        product.pop("body")
        product["body_state"] = "not_requested"
    native["support_page"] = {"records": records, "after": None, "complete": True}
    seen = []

    def read(connection, demand_id, *, project_id, **kwargs):
        seen.append(kwargs)
        return DemandResult(json_bytes(native))

    monkeypatch.setattr("corpus_structure.semantic.demand_queries.read_demand_result", read)
    request = DemandQueryRequest(
        project_id="project:A", demand_id="demand:A", view="support", product_id="product:A"
    )
    result = serve_demand_query(None, request)
    assert result["items"] == records
    assert seen[0]["view"] == "support" and seen[0]["scope"] == {"product_ids": ["product:A"]}
    assert all(
        "scientific_support_opposition" not in row and "asserted_field_fact" not in row
        for row in result["items"]
    )
    source = serve_demand_query(None, request.model_copy(update={"view": "sources"}))
    assert source["items"] == [records[2]]
