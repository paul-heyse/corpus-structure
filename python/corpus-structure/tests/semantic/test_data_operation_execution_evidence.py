"""Original transport receipts remain typed, closed and outside product meaning."""

import copy
import json
from dataclasses import asdict
from typing import Any

import pytest
from jsonschema import ValidationError

from corpus_structure.methods.native_host import NativeExecutionReceipt
from corpus_structure.semantic.data_operation_execution_evidence import (
    SOURCE,
    bind_execution_evidence,
    execution_evidence_schema,
)
from corpus_structure.semantic.data_operation_ports import PortCompletion
from corpus_structure.semantic.data_operation_storage import native_protocol_sources
from corpus_structure.semantic.data_operation_wire import validate_wire_schema, wire_contracts
from corpus_structure.semantic.identity import canonical_bytes
from corpus_structure.semantic.types import SourceArtifact


def receipt():
    return NativeExecutionReceipt(
        "host-generation", "host-request", "spacy", "profile", "observed-runtime", "input", "output"
    )


def test_actual_transport_fields_are_bound_to_exact_native_attempt():
    fence = dict(request_id="native-request", generation=2, task_id=3, attempt=4, holder="owner")
    value = bind_execution_evidence(
        canonical_bytes([asdict(receipt())]), fence=fence, runtime_id="native-runtime"
    )
    assert value["request_id"] == "native-request"
    assert value["host_receipts"][0]["request_id"] == "host-request"
    assert value["host_receipts"][0]["runtime"] == "observed-runtime"
    assert value["runtime_id"] == "native-runtime"
    assert value["generation"] == 2 and value["attempt"] == 4
    assert PortCompletion("op", (), outcome="empty").outcome == "empty"


@pytest.mark.parametrize("mutation", ["extra", "missing", "type", "empty"])
def test_original_host_receipt_schema_remains_closed(mutation):
    record: dict[str, Any] = asdict(receipt())
    if mutation == "extra":
        record["invented_source"] = "anything"
    elif mutation == "missing":
        record.pop("profile")
    elif mutation == "type":
        record["host_generation"] = 7
    else:
        record["runtime"] = ""
    with pytest.raises(ValidationError):
        bind_execution_evidence(
            canonical_bytes([record]),
            fence=dict(
                request_id="r",
                generation=1,
                task_id=1,
                attempt=1,
                holder="owner",
            ),
            runtime_id="runtime",
        )


def test_captured_companion_schema_is_required_and_owns_wire_interpretation():
    sources = native_protocol_sources()
    with pytest.raises(ValueError, match="captured schema"):
        wire_contracts(tuple(source for source in sources if source.name != SOURCE))
    schema = json.loads(execution_evidence_schema())
    altered = copy.deepcopy(schema)
    altered["properties"]["runtime_id"]["const"] = "only-this-runtime"
    captured = tuple(
        SourceArtifact(source.name, canonical_bytes(altered)) if source.name == SOURCE else source
        for source in sources
    )
    completion = wire_contracts(captured)["retain_data_completion_intent"]["input"]
    evidence = bind_execution_evidence(
        b"[]",
        fence=dict(request_id="r", generation=1, task_id=1, attempt=1, holder="h"),
        runtime_id="runtime",
    )
    request = {
        **{
            key: evidence[key]
            for key in ("request_id", "generation", "task_id", "attempt", "holder")
        },
        "runtime_id": "runtime",
        "completion": dict(
            outcome="success",
            outputs=[],
            inputs=[],
            support=[],
            implementation_revision="implementation",
            execution_evidence=evidence,
        ),
    }
    with pytest.raises(ValueError, match="only-this-runtime"):
        validate_wire_schema(completion, request)


def test_cpu_receipt_keeps_matched_process_facts_without_product_or_reply_copy():
    from corpus_structure.semantic.cpu_receipts import CPUExecutionReceipt

    original = CPUExecutionReceipt("a" * 64, 23, True, 1, b'[{"num_threads":1,"user_api":"blas"}]')
    value = bind_execution_evidence(
        None,
        cpu_content=canonical_bytes(original.record()),
        fence=dict(request_id="r", generation=1, task_id=2, attempt=3, holder="h"),
        runtime_id="runtime",
    )
    assert value["host_receipts"] == []
    assert value["cpu_receipts"][0] == original.record()
    assert "content" not in value["cpu_receipts"][0]
    decoded = original.native_pools()
    decoded[0]["num_threads"] = 99
    assert original.native_pools()[0]["num_threads"] == 1
