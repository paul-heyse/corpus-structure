"""Public governed selection retains exact scope and its native cut across pages."""

import pytest
from pydantic import ValidationError

from corpus_structure.semantic.continuation_codec import DEMAND_MEMBER_CURSOR, encode_cursor
from corpus_structure.semantic.demand_queries import demand_cursor_selection
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


def test_governed_scope_distinguishes_omitted_and_explicit_json_context():
    from corpus_structure.semantic.demand_queries import DemandQueryRequest

    governed = GovernedDemandQueryRequest(project_id="p", selection_name="working")
    direct = DemandQueryRequest(project_id="p", demand_id="d")
    assert "analyzed_scope" not in governed.selection()
    assert "analyzed_scope" not in direct.selection()
    for context in (None, ["page", 2]):
        update = {"analyzed_scope": context}
        assert governed_scope(governed.model_copy(update=update)) == update
        assert governed.model_copy(update=update).selection()["analyzed_scope"] == context
        assert direct.model_copy(update=update).selection()["analyzed_scope"] == context


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


def _pinned_cursor(request):
    return encode_cursor(
        dict(
            version=DEMAND_MEMBER_CURSOR,
            implementation="implementation",
            selection=demand_cursor_selection(request, request.selection(), 1),
            cut="cut",
            read_id="read:old",
            position=None,
            generation=1,
        )
    )


def test_governed_cursor_rejects_changed_selection_before_acquisition():
    request = GovernedDemandQueryRequest(project_id="p", selection_name="working")
    cursor = _pinned_cursor(request.model_copy(update={"selection_name": "different"}))
    with pytest.raises(ValueError, match="exact governed selection"):
        serve_governed_demand_query(None, request.model_copy(update={"cursor": cursor}))


@pytest.mark.parametrize("mode", ["current", "last-settled"])
def test_governed_cursor_acquires_exact_pin_and_generation(monkeypatch, mode):
    request = GovernedDemandQueryRequest(
        project_id="p", selection_name="working", mode=mode, analyzed_scope=None
    )
    cursor = _pinned_cursor(request)
    freshness = dict(read_id="read:old", demand_id="d", selection_generation=1)

    class Storage:
        def __init__(self, connection):
            pass

        def read_governed_selection(self, selection):
            assert selection == dict(
                project_id="p",
                selection_name="working",
                scope={"analyzed_scope": None},
                mode=mode,
                read_id="read:old",
                selection_generation=1,
            )
            return freshness

    def serve(connection, exact, **kwargs):
        assert exact.cursor == cursor and exact.demand_id == "d"
        assert exact.selection()["analyzed_scope"] is None
        assert kwargs["read_id"] == "read:old"
        assert kwargs["governance"]["generation"] == 1
        return "selected read"

    monkeypatch.setattr("corpus_structure.semantic.governed_reads.DataOperationStorage", Storage)
    monkeypatch.setattr("corpus_structure.semantic.demand_queries.serve_demand_query", serve)
    continued = request.model_copy(update={"cursor": cursor})
    assert serve_governed_demand_query(None, continued) == "selected read"
    freshness["selection_generation"] = 2
    with pytest.raises(ValueError, match="acquired read or generation"):
        serve_governed_demand_query(None, continued)
