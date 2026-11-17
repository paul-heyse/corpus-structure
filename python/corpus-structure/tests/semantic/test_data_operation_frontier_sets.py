"""Page-local progress, waiting watermarks and native set correspondence."""

from types import SimpleNamespace
from typing import Any, cast

import pytest

from corpus_structure.semantic import data_operation_demands as demands
from corpus_structure.semantic import data_operation_storage as storage_module
from semantic.data_operation_declaration_support import model, operation
from semantic.test_data_operation_demands import freeze


def page(compiled):
    return {
        "demand_id": "demand", "read_id": "read", "intent": freeze(compiled).record,
        "obligations": [
            {"obligation_id": str(i), "operation_id": "op:result", "fate": "attached",
             "request_id": "request:" + str(i), "generation": 1,
             "inputs_watermark": "inputs:one"}
            for i in range(3)
        ],
        "uses": [],
    }


def test_attach_set_preserves_siblings_and_counts_only_page_changes(monkeypatch):
    compiled = model(operation("op:result"))
    snapshot = page(compiled)
    calls = []
    bound = tuple(demands.BoundDataRequest(
        obligation=str(i), operation="op:result", subject="subject",
        request=b"{}", request_id="request:" + str(i), admission=b"{}",
        binding=b"{}", resolved=cast(Any, object()), binding_result=cast(Any, object()),
    ) for i in range(3))

    def attach(payload):
        calls.append(payload)
        return {"items": [
            {"state": "attached", "result": {
                "request_id": "request:0", "generation": 1, "fate": "attached", "use_id": "new-read-use",
            }},
            {"state": "refused", "sqlstate": "22023", "reason": "controlled refusal"},
            {"state": "fulfilled", "result": {
                "request_id": "request:2", "generation": 2, "fate": "fulfilled",
            }},
        ]}

    planner = demands.DemandPlanner(compiled, cast(Any, SimpleNamespace(attach_data_requests=attach)))
    monkeypatch.setattr(planner, "bound_requests", lambda *_args, **_kw: bound)
    monkeypatch.setattr(demands, "ReadyDataRequest", lambda **values: SimpleNamespace(**values))
    ready = planner.ready(snapshot, authorization=b"authorization")
    assert len(calls) == 1 and len(calls[0]["items"]) == 3
    assert calls[0]["read_id"] == "read"
    assert tuple(value.obligation for value in ready) == ("0",)
    assert planner.logical_progress == 1  # New read/use identity alone is no progress.
    assert planner.fulfilled_request_ids == ("request:2",)
    assert len(planner.refusals) == 1 and "controlled refusal" in str(planner.refusals[0])


@pytest.mark.parametrize("changed,retained", [(False, False), (True, False), (False, True)])
def test_waiting_skip_requires_same_native_watermark_and_not_retained(monkeypatch, changed, retained):
    compiled = model(operation("op:result"))
    snapshot = page(compiled)
    snapshot["obligations"] = snapshot["obligations"][:1]
    snapshot["obligations"][0]["fate"] = "awaiting-inputs"
    snapshot["uses"] = [{
        "obligation_id": "0", "fate": "awaiting-inputs",
        "selection": {"inputs_watermark": "inputs:old" if changed else "inputs:one"},
    }]
    snapshot.update(project_id="project", trust_snapshot={})
    snapshot["obligations"][0].update(subject="subject", original_source="source", analyzed_scope={})
    calls = []

    class BindingReached(Exception):
        pass

    def projection(*args, **kwargs):
        calls.append(1)
        raise BindingReached

    monkeypatch.setattr(storage_module, "admitted_data_projection", projection)
    planner = demands.DemandPlanner(compiled, cast(Any, SimpleNamespace(connection=object())))
    if changed or retained:
        with pytest.raises(BindingReached):
            tuple(planner.bound_requests(snapshot, authorization=b"auth", retained=retained))
        assert calls == [1]
    else:
        assert tuple(planner.bound_requests(snapshot, authorization=b"auth")) == ()
        assert calls == []


def test_native_registration_owns_frozen_root_dependency_expansion():
    compiled = model(operation("op:base"), operation("op:result", dependencies=["op:base"]))
    intent = freeze(compiled)
    calls = []

    def register(payload):
        calls.append(payload)
        return {"demand_id": "demand", "selection": intent.record, "inserted_obligations": 2}

    # No scalar expansion method exists on this storage double.
    planner = demands.DemandPlanner(compiled, cast(Any, SimpleNamespace(register_data_demand=register)))
    result = planner.register(intent, project="project", release="release", runtime="runtime")
    assert len(calls) == 1 and result["inserted_obligations"] == 2
    assert set(calls[0]["selection"]["root_operations"]) == {"op:base", "op:result"}


def test_demand_result_preserves_native_waiting_watermark():
    from corpus_structure.semantic.data_operation_json import json_bytes
    from corpus_structure.semantic.demand_results import DemandResult

    native = {
        "demand_id": "demand", "project_id": "project", "release_id": "release", "runtime_id": "runtime",
        "read_id": "read", "read_snapshot": "1:2:", "frontier_at": "2026-11-17T00:00:00Z",
        "selection": {}, "trust_snapshot": {}, "scope": {}, "view": "frontier", "continuation": None,
        "obligations": [{"obligation_id": "obligation", "inputs_watermark": "native:watermark"}],
        "uses": [{"obligation_id": "obligation", "fate": "awaiting-inputs",
                  "selection": {"inputs_watermark": "native:watermark", "reasons": []}}], "populations": [],
    }
    result = DemandResult(json_bytes(native))
    report = result.report()
    assert report["obligations"] == native["obligations"]
    assert report["uses"] == native["uses"]
    report["obligations"][0]["inputs_watermark"] = "mutated"
    assert result.record["obligations"][0]["inputs_watermark"] == "native:watermark"
