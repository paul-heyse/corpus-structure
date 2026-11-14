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
from semantic.data_operation_kernel_support import STORAGE


def receipt():
    return NativeExecutionReceipt(
        "host-generation", "host-request", "spacy", "profile", "observed-runtime", "input", "output"
    )


@pytest.mark.parametrize(
    "foreign", [None, "request_id", "generation", "task_id", "attempt", "missing"]
)
def test_provider_scatter_receipt_preserves_real_cohort_and_exact_logical_fence(foreign):
    from corpus_structure.methods.characterization_resources import (
        LogicalProviderMember,
        ProviderExecutionReceipt,
    )
    from corpus_structure.methods.native_host import payload_digest

    fence = dict(request_id="request:source", generation=2, task_id=3, attempt=4, holder="owner")
    member = {name: fence[name] for name in ("request_id", "generation", "task_id", "attempt")}
    if foreign in member:
        member[foreign] = "request:other" if foreign == "request_id" else 99
    logical = LogicalProviderMember(
        **member, member="source:window", start=0, count=1, input_digest="original-input"
    )
    works = (("other-work", 0, 1), ("actual-work", 1, 1))
    members = ("other-input", "original-input")
    original = ProviderExecutionReceipt(
        "actual-work",
        payload_digest({"works": works, "members": members}),
        1,
        1,
        ("original-input",),
        () if foreign == "missing" else (logical,),
        (receipt(),),
        members,
        works,
    )

    def bind():
        return bind_execution_evidence(
            None,
            fence=fence,
            runtime_id="runtime",
            provider_content=canonical_bytes([asdict(original)]),
        )

    if foreign is not None:
        with pytest.raises(ValueError, match="logical receipt differs"):
            bind()
        return
    value = bind()
    assert value["provider_receipts"] == json.loads(canonical_bytes([asdict(original)]))
    assert value["host_receipts"] == []
    assert value["provider_receipts"][0]["physical"][0]["request_id"] == "host-request"


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


def test_pdf_receipt_keeps_original_sealed_publisher_separate_from_admitting_attempt():
    from corpus_structure.semantic.pdf_publication import (
        PdfExecutionReceipt,
        PublishedPdfDocumentRef,
    )

    original = PdfExecutionReceipt(
        PublishedPdfDocumentRef(
            "build",
            3,
            "product",
            "logical",
            "release",
            "source",
            "schema",
            "recipe",
            "frozen",
            "native",
        ),
        publisher_attempt=1,
        publisher_holder="sealed-owner",
    )
    value = bind_execution_evidence(
        None,
        pdf_content=canonical_bytes(asdict(original)),
        runtime_id="runtime",
        fence=dict(request_id="r", generation=1, task_id=3, attempt=2, holder="current-owner"),
    )
    assert value["holder"] == "current-owner" and value["attempt"] == 2
    assert value["pdf_receipts"] == [asdict(original)]
    assert value["pdf_receipts"][0]["publisher_attempt"] == 1
    assert value["host_receipts"] == [] and value["cpu_receipts"] == []
    with pytest.raises(TypeError, match="immutable bytes"):
        PortCompletion("op", (), pdf_execution_evidence=bytearray(b"{}"))  # type: ignore[arg-type]


@pytest.mark.parametrize("foreign", ["request_id", "generation", "task_id", "attempt"])
@pytest.mark.parametrize(
    "ddo_kernel",
    [STORAGE],
    indirect=True,
    ids=["provider-fence"],
)
def test_native_retention_refuses_foreign_provider_logical_fence(ddo_kernel, foreign):
    from sqlalchemy import text
    from sqlalchemy.exc import DBAPIError

    from corpus_structure.methods.characterization_resources import (
        LogicalProviderMember,
        ProviderExecutionReceipt,
    )
    from corpus_structure.methods.native_host import payload_digest
    from corpus_structure.semantic.data_operation_identity import semantic_value
    from corpus_structure.semantic.data_operation_storage import DataOperationStorage
    from semantic.data_operation_demand_support import attach, claim

    _, _, _, attached = attach(ddo_kernel)
    fence = claim(ddo_kernel, attached)
    logical = LogicalProviderMember(
        **{name: fence[name] for name in ("request_id", "generation", "task_id", "attempt")},
        member="original-window",
        start=0,
        count=1,
        input_digest="original-input",
    )
    works, members = (("actual-work", 0, 1),), ("original-input",)
    original = ProviderExecutionReceipt(
        "actual-work",
        payload_digest({"works": works, "members": members}),
        0,
        1,
        members,
        (logical,),
        (receipt(),),
        members,
        works,
    )
    evidence = bind_execution_evidence(
        None,
        fence=fence,
        runtime_id=ddo_kernel["runtime"],
        provider_content=canonical_bytes([asdict(original)]),
    )
    evidence["provider_receipts"][0]["logical_members"][0][foreign] = (
        "request:foreign" if foreign == "request_id" else 999
    )
    completion = dict(
        outcome="success",
        inputs=[],
        support=[],
        implementation_revision="native-test-source-v1",
        outputs=[
            dict(
                role="result",
                position=0,
                multiplicity=1,
                product=dict(kind_contract=ddo_kernel["kind"], body=semantic_value(1), members=[]),
            )
        ],
        execution_evidence=evidence,
    )
    with ddo_kernel.purpose("write").begin() as connection:
        with (
            pytest.raises(DBAPIError, match="provider logical receipt differs"),
            connection.begin_nested(),
        ):
            DataOperationStorage(connection).invoke(
                "retain_data_completion_intent",
                {
                    **fence,
                    "runtime_id": ddo_kernel["runtime"],
                    "completion": completion,
                },
            )
    with ddo_kernel["engine"].connect() as connection:
        assert (
            connection.scalar(
                text("SELECT count(*) FROM ops.data_completion_intent WHERE request_id=:request"),
                {"request": fence["request_id"]},
            )
            == 0
        )
