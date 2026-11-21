"""Managed reporting binds exact native demand custody, never synthetic run IDs."""

from corpus_structure.semantic.data_operation_json import (
    finite_json_loads,
    json_bytes,
    native_json_loads,
)
from corpus_structure.semantic.demand_wire import interpret_demand_record


def record_native_demand(invocation, snapshot, target):
    bindings = {
        "demand_id": snapshot["demand_id"],
        "project": snapshot["project_id"],
        "release_id": snapshot["release_id"],
        "runtime_id": snapshot["runtime_id"],
    }
    invocation.manifest.details["observation_target"] = target.model_dump(mode="json")
    invocation.bind_observations(**bindings)
    invocation.stage("demand_registered", **bindings)


def native_demand_result(result):
    return {
        "demand_id": result.demand_id,
        "snapshot": interpret_demand_record(native_json_loads(result.snapshot)),
        "snapshot_standing": result.snapshot_standing,
        "receipt_count": result.receipt_count,
        "receipts_truncated": result.receipts_truncated,
        "receipts": [finite_json_loads(value) for value in result.receipts],
    }


def retain_native_demand_result(invocation, result):
    report = native_demand_result(result)
    path = invocation.directory / "native.json"
    path.write_bytes(json_bytes(report))
    invocation.publish("native", path)
    if result.receipt_count:
        invocation.observe(
            "native_publication",
            "native publication receipts retained",
            assurance="native",
            operational_phase="publication",
            receipt_count=result.receipt_count,
            receipt_unit="publication_receipts",
            receipts_truncated=result.receipts_truncated,
        )
    return report
