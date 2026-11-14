"""Service routing preserves native continuation meaning; no admission is simulated."""

from __future__ import annotations

from typing import cast

import pytest
from sqlalchemy import Connection

from corpus_structure.semantic import data_operation_service as service
from semantic.data_operation_kernel_support import STORAGE


def test_service_read_preserves_full_native_continuation(monkeypatch):
    from semantic.data_operation_binding_support import WireCheckedStorage

    connection = cast(Connection, object())
    selection = {
        "version": "data-demand-intent-v1",
        "model": "a" * 64,
        "roots": [
            {"subject": "subject:one", "original_source": "source:one", "analyzed_scope": {}}
        ],
        "targets": ["urn:operation"],
        "root_operations": ["urn:operation"],
        "operations": [
            {
                "operation": "urn:operation",
                "parameters": {},
                "choices": {},
                "replicate": None,
                "dependencies": [],
                "definition": "definition:one",
                "recipe": "recipe:one",
                "eligibility": "eligibility:one",
                "parameter_meaning": ["mapping", []],
            }
        ],
        "discovery": [],
        "inference": "inference:one",
        "execution_profile": "execution:one",
    }
    pins = {
        "demand_id": "demand:one",
        "selection": selection,
        "read_id": "read:one",
        "read_snapshot": "1:2:",
        "frontier_at": "2026-11-13T00:00:00Z",
        "trust_snapshot": {"scope": 2},
        "after": "obligation:one",
        "limit": 7,
        "view": "products",
    }
    reply = {
        "demand_id": "demand:one",
        "project_id": "project:one",
        "release_id": "release:one",
        "runtime_id": "runtime:one",
        "selection": selection,
        "intent": selection,
        "root": selection["roots"],
        "trust_snapshot": {"scope": 2},
        "uses": [],
        "obligations": [],
        "populations": [],
        "continuation": pins,
        "read_id": "read:one",
        "read_snapshot": "1:2:",
        "frontier_at": "2026-11-13T00:00:00Z",
        "view": "products",
    }
    storage = WireCheckedStorage({"read_demand_result": reply})
    monkeypatch.setattr(service, "DataOperationStorage", lambda connection: storage)
    result = service.read_data_demand(connection, "demand:one", continuation=pins)
    assert storage.calls == [("read_demand_result", pins)]
    assert result["continuation"] == pins
    assert pins["limit"] == 7
    with pytest.raises(ValueError, match="another demand"):
        service.read_data_demand(connection, "demand:other", continuation=pins)
    with pytest.raises(ValueError, match="view differs"):
        service.read_data_demand(connection, "demand:one", continuation=pins, view="frontier")
    assert len(storage.calls) == 1


@pytest.mark.parametrize("ddo_kernel", [STORAGE], indirect=True, ids=["storage"])
def test_native_service_creation_read_and_cancellation_preserve_original_pins(ddo_kernel):
    from corpus_structure.semantic.data_operation_demands import RootSubject, freeze_demand

    intent = freeze_demand(
        ddo_kernel["model"],
        roots=(RootSubject("subject:one", "source:test", b'{"page":1}'),),
        targets=("urn:ddo-test:source",),
        inference="inference:test",
        execution_profile="execution:test",
    )
    request = service.CreateDataDemand(
        project_id="ddo-test",
        release_id=ddo_kernel["prepared"].release_id,
        runtime_id=ddo_kernel["runtime"],
        intent=intent.record,
    )
    with ddo_kernel["engine"].begin() as connection:
        created = service.create_data_demand(connection, request)
        assert created["release_id"] == request.release_id
        assert created["runtime_id"] == request.runtime_id
        assert created["selection"] == intent.record
        assert created["obligations"][0]["subject"] == "subject:one"
        demand = created["demand_id"]
        current = service.read_data_demand(connection, demand, limit=1)
        assert current["read_id"] != created["read_id"]
        cancelled = service.cancel_data_demand(connection, demand, reason="operator cancelled")
        assert cancelled["state"] == "cancelled"
        assert service.read_data_demand(connection, demand)["state"] == "cancelled"
