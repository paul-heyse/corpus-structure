"""Current selected characterization preserves the native cut and exact scoped selection."""

from decimal import Decimal

import pytest
from pydantic import ValidationError

from corpus_structure.serve.characterization import DemandCharacterizationRequest, inspect_demand_characterization


@pytest.mark.parametrize("inventory,view,record_type,containers", [
    ("summary", "members", None, True),
    ("occurrences", "members", "occurrence", False),
    ("annotations", "members", "annotation", False),
    ("terms", "members", "term", False),
    ("memberships", "members", "membership", False),
    ("choices", "members", "choice", False),
    ("coverage", "coverage", None, False),
])
@pytest.mark.parametrize("source", ["omitted", None, "original:selected"])
def test_inventory_delegates_real_selected_population_without_losing_null_source_semantics(monkeypatch, inventory, view, record_type, containers, source):
    from corpus_structure.semantic import contribution_queries
    received = []
    result = dict(cut={"read_id": "read:actual", "scope": {"fraction": Decimal("0.123456789012345678901")}},
        items=[], obligations=[{"fate": "waiting"}], uses=[], populations=[{"status": "incomplete"}],
        page_complete=False, continuation="exact:continuation", knowledge="unknown")
    def read(connection, request):
        received.append(request)
        return result
    monkeypatch.setattr(contribution_queries, "read_demand_contributions", read)
    value = dict(project_id="project:selected", demand_id="demand:selected", inventory=inventory,
        product_id="product:selected", member_id="membership:off-page", cursor="previous:continuation", limit=2)
    if source != "omitted":
        value["original_source"] = source
    selected = DemandCharacterizationRequest.model_validate(value)
    actual = inspect_demand_characterization(None, selected)
    assert actual is result
    request = received[0]
    assert request.view == view and request.record_type == record_type
    assert request.containers_only is containers
    assert request.product_id == "product:selected" and request.member_id == "membership:off-page"
    assert request.cursor == "previous:continuation" and request.limit == 2
    assert ("original_source" in request.model_fields_set) is (source != "omitted")
    assert request.original_source == (None if source == "omitted" else source)
    assert actual["knowledge"] == "unknown" and not actual["page_complete"]


def test_current_characterization_refuses_task_layer_pins_and_unbounded_reads():
    for values in ({"run_id": 1, "task_id": 2, "product_key": "view", "content_digest": "a"*64},
                   {"limit": 0}, {"max_bytes": 1}, {"inventory": "reading", "layer_key": "old-layer"}):
        with pytest.raises(ValidationError):
            DemandCharacterizationRequest.model_validate({"project_id": "project:selected", "demand_id": "demand:selected", **values})
