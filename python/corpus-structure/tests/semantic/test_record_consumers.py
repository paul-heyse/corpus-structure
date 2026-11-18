"""Current selected record adapters preserve exact bodies and authoritative coordinates.

Controlled native pages establish adapter contracts, not native qualification.
"""

from contextlib import contextmanager
from decimal import Decimal

import pytest
from pydantic import ValidationError

from corpus_structure.semantic.data_operation_json import json_bytes, json_loads
from corpus_structure.semantic.demand_queries import DemandQueryRequest, serve_demand_query
from corpus_structure.semantic.demand_results import DemandResult
from semantic.demand_result_support import demand_result_page


@pytest.fixture
def selected_records(monkeypatch):
    seen = []

    def read(connection, demand_id, *, project_id, **kwargs):
        seen.append(dict(demand_id=demand_id, project_id=project_id, **kwargs))
        return DemandResult(json_bytes(demand_result_page()))

    monkeypatch.setattr("corpus_structure.semantic.demand_queries.read_demand_result", read)
    return seen


def test_current_records_keep_actual_product_member_episode_and_numeric_value(selected_records):
    result = serve_demand_query(
        None, DemandQueryRequest(project_id="project:A", demand_id="demand:A")
    )
    assert [(row["product_id"], row["member_id"]) for row in result["items"]] == [
        ("product:A", None),
        ("product:A", "first"),
        ("product:A", "second"),
    ]
    first = result["items"][1]
    assert first["body"]["amount"] == Decimal("12.340")
    assert first["analyzed_scope"] == {"scale": Decimal("1.20")}
    assert first["subject_definition"] == "document"
    assert first["original_source"] == "source:A"
    assert first["use_id"] == "use:A" and first["derivation_id"] == "episode:original"
    assert first["multiplicity"] == 2
    assert "scientific_support" not in first and "accepted" not in first
    assert selected_records[0]["view"] == "products"


def test_current_records_cli_consumes_exact_project_demand_and_explicit_null_source(
    cli, monkeypatch
):
    from corpus_structure.semantic import runtime

    seen = []

    @contextmanager
    def engine(settings, application_name, *, purpose):
        assert purpose == "read"

        class Engine:
            @contextmanager
            def begin(self):
                yield object()

        yield Engine()

    def query(connection, request):
        seen.append(request)
        return {"items": [{"body": {"amount": Decimal("0.123456789012345678901")}}]}

    monkeypatch.setattr(runtime, "open_runtime_engine", engine)
    monkeypatch.setattr("corpus_structure.cli.selected_results.serve_demand_query", query)
    result = cli(
        "records",
        "list",
        "--project",
        "project:A",
        "--demand",
        "demand:A",
        "--without-original-source",
        "--json",
    )
    assert result.exit_code == 0, (result.output, result.exception)
    assert json_loads(result.stdout)["items"][0]["body"]["amount"] == Decimal(
        "0.123456789012345678901"
    )
    assert seen[0].project_id == "project:A" and seen[0].demand_id == "demand:A"
    assert seen[0].original_source is None and "original_source" in seen[0].model_fields_set
    assert cli("retained-records", "list", "--run", "1", "--json").exit_code != 0
    assert len(seen) == 1


@pytest.mark.parametrize(
    "old",
    [{"run_id": 1}, {"review_cut_id": 1}, {"source_view_ids": [1]}, {"include_diagnostics": True}],
)
def test_current_record_request_refuses_retired_integer_and_diagnostic_contracts(old):
    with pytest.raises(ValidationError):
        DemandQueryRequest.model_validate(
            {"project_id": "project:A", "demand_id": "demand:A", **old}
        )


def test_current_record_filter_keeps_zero_match_frontier_without_absence_claim(selected_records):
    result = serve_demand_query(
        None,
        DemandQueryRequest(project_id="project:A", demand_id="demand:A", member_id="unselected"),
    )
    assert result["items"] == []
    assert result["obligations"] == [{"obligation_id": "obligation:A", "fate": "fulfilled"}]
    assert result["uses"][0]["derivation_id"] == "episode:original"
    assert result["knowledge"] == "unknown"
