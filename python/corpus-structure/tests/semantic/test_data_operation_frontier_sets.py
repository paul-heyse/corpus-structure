"""Page-local progress, exact origin observation and native set correspondence."""

from types import SimpleNamespace
from typing import Any, NotRequired, TypedDict, cast

import pytest

from corpus_structure.semantic import data_operation_demands as demands
from corpus_structure.semantic import data_operation_storage as storage_module
from corpus_structure.semantic._data_operation_wire import WireDemandIntent
from semantic.data_operation_declaration_support import model, operation
from semantic.test_data_operation_demands import freeze


class FrontierObligation(TypedDict):
    obligation_id: str
    operation_id: str
    fate: str
    request_id: str
    generation: int
    binding_origin_changed: NotRequired[bool]
    subject: NotRequired[str]
    original_source: NotRequired[str]
    analyzed_scope: NotRequired[dict[str, object]]


class WaitingUse(TypedDict):
    obligation_id: str
    fate: str
    selection: dict[str, str]


class FrontierPage(TypedDict):
    demand_id: str
    read_id: str
    intent: WireDemandIntent
    obligations: list[FrontierObligation]
    uses: list[WaitingUse]
    project_id: NotRequired[str]
    trust_snapshot: NotRequired[dict[str, int]]


def page(compiled) -> FrontierPage:
    return {
        "demand_id": "demand",
        "read_id": "read",
        "intent": freeze(compiled).record,
        "obligations": [
            {
                "obligation_id": str(i),
                "operation_id": "op:result",
                "fate": "attached",
                "request_id": "request:" + str(i),
                "generation": 1,
                "binding_origin_changed": False,
            }
            for i in range(3)
        ],
        "uses": [],
    }


def test_attach_set_preserves_siblings_and_counts_only_page_changes(monkeypatch):
    compiled = model(operation("op:result"))
    snapshot = page(compiled)
    calls = []
    bound = tuple(
        demands.BoundDataRequest(
            obligation=str(i),
            operation="op:result",
            subject="subject",
            request=b"{}",
            request_id="request:" + str(i),
            admission=b"{}",
            binding=b"{}",
            resolved=cast(Any, object()),
            binding_result=cast(Any, object()),
        )
        for i in range(3)
    )

    def attach(payload):
        calls.append(payload)
        return {
            "items": [
                {
                    "state": "attached",
                    "result": {
                        "request_id": "request:0",
                        "generation": 1,
                        "fate": "attached",
                        "use_id": "new-read-use",
                    },
                },
                {"state": "refused", "sqlstate": "22023", "reason": "controlled refusal"},
                {
                    "state": "fulfilled",
                    "result": {
                        "request_id": "request:2",
                        "generation": 2,
                        "fate": "fulfilled",
                    },
                },
            ]
        }

    planner = demands.DemandPlanner(
        compiled, cast(Any, SimpleNamespace(attach_data_requests=attach))
    )
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
def test_waiting_skip_requires_no_new_native_origin_and_not_retained(
    monkeypatch, changed, retained
):
    compiled = model(operation("op:result"))
    snapshot = page(compiled)
    snapshot["obligations"] = snapshot["obligations"][:1]
    snapshot["obligations"][0]["fate"] = "awaiting-inputs"
    snapshot["obligations"][0]["binding_origin_changed"] = changed
    snapshot["uses"] = [
        {
            "obligation_id": "0",
            "fate": "awaiting-inputs",
            "selection": {"read_id": "read:binding"},
        }
    ]
    snapshot.update(project_id="project", trust_snapshot={})
    snapshot["obligations"][0].update(
        subject="subject", original_source="source", analyzed_scope={}
    )
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
    planner = demands.DemandPlanner(
        compiled, cast(Any, SimpleNamespace(register_data_demand=register))
    )
    result = planner.register(intent, project="project", release="release", runtime="runtime")
    assert len(calls) == 1 and result["inserted_obligations"] == 2
    assert set(calls[0]["selection"]["root_operations"]) == {"op:base", "op:result"}


def test_demand_result_preserves_native_waiting_read_identity():
    from corpus_structure.semantic.data_operation_json import json_bytes
    from corpus_structure.semantic.demand_results import DemandResult
    from semantic.demand_result_support import demand_result_page

    native = demand_result_page()
    native["obligations"][0].update(fate="awaiting-inputs", historical_fate="awaiting-inputs")
    native["uses"][0].update(
        fate="awaiting-inputs",
        historical_fate="awaiting-inputs",
        selection={"read_id": "read:binding", "reasons": []},
        products=[],
    )
    result = DemandResult(json_bytes(native))
    report = result.report()
    assert report["obligations"] == native["obligations"]
    assert report["uses"] == native["uses"]
    report["uses"][0]["selection"]["read_id"] = "mutated"
    assert result.record["uses"][0]["selection"]["read_id"] == "read:binding"
