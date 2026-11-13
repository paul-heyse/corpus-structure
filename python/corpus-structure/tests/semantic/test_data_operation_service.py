"""Service routing preserves native continuation meaning; no admission is simulated."""

from __future__ import annotations

from typing import cast

import pytest
from sqlalchemy import Connection

from corpus_structure.semantic import data_operation_service as service

from .test_data_operation_storage import ddo_kernel_engine as ddo_kernel_engine
from .test_data_operation_storage import kernel as kernel


def test_service_read_preserves_full_native_continuation(monkeypatch):
    calls = []
    connection = cast(Connection, object())

    class Storage:
        def __init__(self, connection):
            pass

        def invoke(self, operation, payload):
            calls.append((operation, payload))
            return {"demand_id": payload["demand_id"], "continuation": payload}

    monkeypatch.setattr(service, "DataOperationStorage", Storage)
    pins = {
        "demand_id": "demand:one",
        "selection": {"model": "frozen"},
        "read_id": "read:one",
        "read_snapshot": "1:2:",
        "frontier_at": "now",
        "trust_snapshot": {"scope": 2},
        "after": "obligation:one",
        "limit": 7,
        "view": "products",
    }
    result = service.read_data_demand(connection, "demand:one", continuation=pins)
    assert calls == [("read_demand_result", pins)]
    assert result["continuation"] == pins
    assert pins["limit"] == 7
    with pytest.raises(ValueError, match="another demand"):
        service.read_data_demand(connection, "demand:other", continuation=pins)
    with pytest.raises(ValueError, match="view differs"):
        service.read_data_demand(connection, "demand:one", continuation=pins, view="frontier")
    assert len(calls) == 1


def test_native_service_creation_read_and_cancellation_preserve_original_pins(kernel):
    from corpus_structure.semantic.data_operation_demands import RootSubject, freeze_demand

    intent = freeze_demand(
        kernel["model"],
        roots=(RootSubject("subject:one", "source:test", b'{"page":1}'),),
        targets=("urn:ddo-test:source",),
        inference="inference:test",
        execution_profile="execution:test",
    )
    request = service.CreateDataDemand(
        project_id="ddo-test",
        release_id=kernel["prepared"].release_id,
        runtime_id=kernel["runtime"],
        intent=intent.record,
    )
    with kernel["engine"].begin() as connection:
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
