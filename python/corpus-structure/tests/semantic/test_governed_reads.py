"""Public governed selection retains exact scope and its native cut across pages."""

import pytest
from pydantic import ValidationError

from corpus_structure.semantic.continuation_codec import encode_cursor
from corpus_structure.semantic.governed_reads import (
    GovernedDemandQueryRequest,
    governed_scope,
    serve_governed_demand_query,
)


def test_governed_scope_distinguishes_omitted_and_explicit_empty_original():
    request = GovernedDemandQueryRequest(project_id="p", selection_name="working")
    assert governed_scope(request) == {}
    selected = request.model_copy(update={"original_source": None, "product_id": "product"})
    assert governed_scope(selected) == {"original_source": None, "product_ids": ["product"]}
    with pytest.raises(ValidationError):
        GovernedDemandQueryRequest.model_validate(
            {"project_id": "p", "selection_name": "working", "demand_id": "d"}
        )


def test_governed_uncovered_selection_has_no_fabricated_result(monkeypatch):
    observed = []
    freshness = dict(
        selection_name="working",
        selection_generation=None,
        state="Unknown",
        last_settled=True,
        demand_id=None,
        read_id=None,
    )

    class Storage:
        def __init__(self, connection):
            pass

        def read_governed_selection(self, request):
            observed.append(("read_governed_selection", request))
            return freshness

    monkeypatch.setattr("corpus_structure.semantic.governed_reads.DataOperationStorage", Storage)
    result = serve_governed_demand_query(
        None,
        GovernedDemandQueryRequest(project_id="p", selection_name="working", mode="last-settled"),
    )
    assert result["freshness"] == freshness
    assert result["cut_id"] is None and result["items"] == [] and result["continuation"] is None
    assert observed == [
        (
            "read_governed_selection",
            {"project_id": "p", "selection_name": "working", "mode": "last-settled", "scope": {}},
        )
    ]


def test_governed_cursor_rejects_changed_selection_before_acquisition():
    cursor = encode_cursor(
        dict(
            version="demand-query-v2",
            implementation="implementation",
            selection="digest",
            request={"demand_id": "d", "read_id": "read:old", "scope": {}, "view": "frontier"},
            cut="cut",
            ordinal=0,
            governance={
                "project_id": "p",
                "selection_name": "different",
                "generation": 1,
                "mode": "current",
            },
        )
    )
    with pytest.raises(ValueError, match="exact governed selection"):
        serve_governed_demand_query(
            None,
            GovernedDemandQueryRequest(project_id="p", selection_name="working", cursor=cursor),
        )
