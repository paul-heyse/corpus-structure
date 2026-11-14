"""Managed reporting binds exact native demand custody, never synthetic run IDs."""

from corpus_structure.semantic.data_operation_json import json_bytes, wire_json_loads


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


def retain_native_demand_result(invocation, result):
    report = {
        "demand_id": result.demand_id,
        "snapshot": wire_json_loads(result.snapshot),
        "snapshot_standing": result.snapshot_standing,
        "receipt_count": result.receipt_count,
        "receipts_truncated": result.receipts_truncated,
        "receipts": [wire_json_loads(value) for value in result.receipts],
    }
    path = invocation.directory / "native.json"
    path.write_bytes(json_bytes(report))
    invocation.publish("native", path)
    return report
