"""Native packets preserve actual repeated exact input pins and independent provenance."""

import json

import pytest

from corpus_structure.semantic.data_operation_demands import (
    DemandPlanner,
    RootSubject,
    freeze_demand,
)
from corpus_structure.semantic.data_operation_external import ExternalDataSession
from corpus_structure.semantic.data_operation_storage import DataOperationStorage
from semantic.data_operation_demand_support import claim, publish, retain
from semantic.external_scenarios import EXTERNAL_INPUTS


@pytest.mark.parametrize("ddo_kernel", [EXTERNAL_INPUTS], indirect=True, ids=["external-inputs"])
def test_native_external_packet_preserves_repeated_pins_order_context_and_provenance(ddo_kernel):
    model = ddo_kernel["model"]
    frozen = freeze_demand(
        model,
        roots=(RootSubject("subject:one", "source:test", b'{"page":1}'),),
        targets=("urn:ddo-test:source",),
        inference="inference:test",
        execution_profile="execution:test",
    )
    with ddo_kernel["engine"].begin() as connection:
        planner = DemandPlanner(model, DataOperationStorage(connection))
        demand = planner.register(
            frozen,
            project="ddo-test",
            release=ddo_kernel["prepared"].release_id,
            runtime=ddo_kernel["runtime"],
        )["demand_id"]
        (producer,) = planner.ready(planner.resume(demand), authorization=b"{}")
        assert producer.operation == "urn:ddo-test:packet-source"
    initial = claim(ddo_kernel, json.loads(producer.native))
    source_receipt = publish(ddo_kernel, initial, retain(ddo_kernel, initial, outputs=(7, 7)))
    with ddo_kernel["engine"].begin() as connection:
        planner = DemandPlanner(model, DataOperationStorage(connection))
        (ready,) = planner.ready(planner.resume(demand), authorization=b"{}")
        assert ready.operation == "urn:ddo-test:source"
    source_fence = claim(ddo_kernel, json.loads(ready.native))
    with ddo_kernel["engine"].begin() as connection:
        packet = DataOperationStorage(connection).retain_external_data_packet({**source_fence, "runtime_id": ddo_kernel["runtime"], "max_bytes": 100000})
    session = ExternalDataSession(ddo_kernel["engine"], "ddo-test")
    leased = session.claim(packet["packet_id"])
    actual = session.read(packet["packet_id"], leased)["packet"]
    assert [item["meaning"] for item in actual["inputs"]] == [["integer", "7"], ["integer", "7"]]
    assert [item["position"] for item in actual["inputs"]] == [0, 1]
    assert [item["multiplicity"] for item in actual["inputs"]] == [1, 1]
    assert actual["inputs"][0]["product_id"] == actual["inputs"][1]["product_id"]
    assert all(
        item["subject"] == "subject:one"
        and item["original_source"] == "source:test"
        and item["analyzed_scope"] == {"page": 1}
        for item in actual["inputs"]
    )
    assert all(
        item["derivation_id"] == source_receipt["derivation_id"]
        for item in actual["binding"]["support"]
    )
