"""Actual CPU process facts remain immutable, typed, and outside semantic products."""

import json

import pytest
from pydantic import TypeAdapter, ValidationError

from corpus_structure.semantic.cpu_receipts import CPUExecutionReceipt
from corpus_structure.semantic.identity import canonical_bytes


def receipt():
    return CPUExecutionReceipt(
        "a" * 64, 123, True, 1, canonical_bytes([{"num_threads": 1, "version": None}])
    )


def test_receipt_schema_and_wire_retain_actual_scalar_constraints_and_json_text():
    adapter = TypeAdapter(CPUExecutionReceipt)
    value = receipt()
    assert json.loads(adapter.dump_json(value)) == value.record()
    assert adapter.validate_json(adapter.dump_json(value), strict=True) == value
    for field, wrong in (
        ("request_digest", "wrong"),
        ("pid", 0),
        ("pid", True),
        ("native_thread_limit", 0),
        ("main_thread", 1),
    ):
        record = value.record()
        record[field] = wrong
        with pytest.raises(ValidationError):
            adapter.validate_json(canonical_bytes(record), strict=True)


def test_cpu_reply_sidecar_copies_actual_diagnostics_without_reply_body_or_cost():
    from corpus_structure.semantic.cpu_execution import CPUReply

    pool = {"num_threads": 1, "version": "actual", "provider_metadata": {"unknown": True}}
    reply = CPUReply(
        "b" * 64,
        b"private body",
        456,
        True,
        cost=b"private cost",
        native_thread_limit=1,
        native_pools=(pool,),
    )
    value = reply.execution_receipt
    pool["version"] = "mutated caller"
    assert value.native_pools()[0]["version"] == "actual"
    assert set(value.record()) == {
        "request_digest",
        "pid",
        "main_thread",
        "native_thread_limit",
        "native_pools_json",
    }
    changed = value.native_pools()
    changed[0]["num_threads"] = 99
    assert value.native_pools()[0]["num_threads"] == 1


@pytest.mark.parametrize("raw", [b"{}", b'[ {"num_threads":1} ]', b"not JSON"])
def test_receipt_refuses_noncanonical_or_nonarray_native_diagnostics(raw):
    with pytest.raises(ValueError):
        CPUExecutionReceipt("a" * 64, 123, True, None, raw)
