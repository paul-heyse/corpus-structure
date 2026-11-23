"""Metadata-only selected inspection never hydrates unrelated result bodies."""

from corpus_structure.semantic.data_operation_json import json_bytes
from corpus_structure.semantic.demand_queries import DemandQueryRequest, serve_demand_query
from corpus_structure.semantic.demand_results import DemandResult
from semantic.demand_result_support import demand_result_page


def test_operation_diagnostics_are_actual_frontier_and_do_not_expand_output_body(monkeypatch):
    native = demand_result_page(empty=True)
    native["view"] = "frontier"
    native["obligations"][0].update(fate="failed", historical_fate="failed")

    def read(connection, demand_id, *, project_id, **kwargs):
        assert kwargs["view"] == "frontier"
        return DemandResult(json_bytes(native))

    monkeypatch.setattr("corpus_structure.semantic.demand_queries.read_demand_result", read)

    def forbidden(self):
        raise AssertionError("frontier inspection must not hydrate products")

    monkeypatch.setattr(DemandResult, "members", forbidden)
    result = serve_demand_query(
        None, DemandQueryRequest(project_id="project:A", demand_id="demand:A", view="operations")
    )
    assert result["items"] == [{"obligation": native["obligations"][0], "uses": []}]
    assert result["items"][0]["obligation"]["fate"] == "failed"
