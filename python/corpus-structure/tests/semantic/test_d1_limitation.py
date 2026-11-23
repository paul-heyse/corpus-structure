"""Controlled diagnostic transport only; no provider execution or accuracy credit."""

import copy
import json
from dataclasses import replace
from hashlib import sha256
from types import SimpleNamespace
from typing import Any, cast

import pytest

from corpus_structure.methods.characterization_resources import (
    LogicalProviderMember,
    ProviderExecutionReceipt,
    ProviderReply,
)
from corpus_structure.methods.model_observation import (
    ordered_native_bytes,
    pm2_cohort_digest,
    pm2_member_digest,
)
from corpus_structure.methods.native_host import NativeExecutionReceipt, payload_digest
from corpus_structure.semantic._data_operation_wire import wire_attempt_fence
from corpus_structure.semantic.d1_limitation import (
    classify_d1_limitation,
    known_d1_failure,
)
from corpus_structure.semantic.data_operation_wire import (
    validate_native_wire,
    validate_wire_schema,
    wire_contracts,
)
from corpus_structure.semantic.model_characterization import QuestionRequest


@pytest.fixture
def controlled():
    fence = dict(request_id="request:one", generation=2, task_id=3, attempt=4, holder="owner")
    pin = dict(
        format="declared-native-source-v1",
        source='["product:source",null]',
        subject="source:one",
        subject_definition="original-source-view",
        document="document:one",
        projection_digest="a" * 64,
        section_pointer="",
        membership="member:original",
        project_id="project:one",
        original_source="document:one",
        analyzed_scope_meaning='["map",[]]',
        source_product="product:source",
        kind_contract="kind:source",
    )
    selection = SimpleNamespace(
        provider="d1",
        native=SimpleNamespace(fingerprint="b" * 64),
        profile=b"controlled-profile",
        runtime=b"controlled-runtime",
    )
    # This is a finite QuestionRequest contract fixture. Production question
    # families are unchanged; seventeen-question refusal belongs to the provider
    # boundary, not an invented current source-question declaration.
    payload = dict(
        state={"source": "12"},
        questions={
            key: dict(type="text", instructions="Copy the numeral.") for key in ("second", "first")
        },
        interpretation=dict(declaration_digest="c" * 64, assessed_scope=dict(pin=pin)),
    )
    request = QuestionRequest(
        cast(
            Any,
            SimpleNamespace(provider="d1", family="controlled-source-question", digest="c" * 64),
        ),
        cast(Any, None),
        0,
        ordered_native_bytes(payload),
    )
    member = pm2_member_digest(payload)
    header = dict(
        provider="d1",
        profile=sha256(selection.profile).hexdigest(),
        runtime=sha256(selection.runtime).hexdigest(),
    )
    batch_receipt = dict(
        version=2,
        header=header,
        members=[member],
        digest=pm2_cohort_digest(header, [member]),
        member_ordinal=0,
    )
    native = dict(
        outcome="limited",
        reason="packed_row_tokens",
        limit=4096,
        row_tokens=[4097],
        batch_receipt=batch_receipt,
    )
    logical = LogicalProviderMember(
        request_id="request:one",
        generation=2,
        task_id=3,
        attempt=4,
        member="scope:question",
        start=0,
        count=1,
        input_digest=payload_digest([payload]),
    )
    physical = NativeExecutionReceipt(
        "host",
        "physical-request",
        "d1",
        selection.native.fingerprint,
        header["runtime"],
        "d" * 64,
        "e" * 64,
    )
    receipt = ProviderExecutionReceipt(
        "work", "f" * 64, 0, 1, (member,), (logical,), (physical,), (member,), (("work", 0, 1),)
    )
    reply = ProviderReply(
        "work", payload_content=ordered_native_bytes({"batch": [native]}), execution_receipt=receipt
    )
    return SimpleNamespace(
        fence=fence, pin=pin, selection=selection, request=request, native=native, reply=reply
    )


def classify(case):
    return classify_d1_limitation(
        case.request,
        case.native,
        case.reply,
        pin=case.pin,
        selection=case.selection,
        member_index=0,
    )


def test_known_limitation_retains_ordered_input_and_original_refusal_without_candidate_standing(
    controlled,
):
    limited = classify(controlled)
    assert limited is not None
    failure = known_d1_failure(limited, fence=controlled.fence, runtime_id="runtime:one")
    assert failure is not None
    diagnostic = failure["d1_limitation"]
    assert diagnostic["request_json"] == controlled.request.content.decode()
    assert diagnostic["request_json"].index('"second"') < diagnostic["request_json"].index(
        '"first"'
    )
    assert diagnostic["native_reply"] == controlled.native
    assert diagnostic["source_pin"] == controlled.pin
    assert diagnostic["standing"] == "unperformed-question-inspection"
    assert diagnostic["inspected_count"] == diagnostic["emitted_count"] == 0
    assert not {"members", "candidates", "inspection_outcome"} & diagnostic.keys()
    evidence = diagnostic["execution_evidence"]
    assert evidence["request_id"] == "request:one" and evidence["attempt"] == 4
    assert evidence["provider_receipts"][0]["physical"][0]["request_id"] == "physical-request"
    assert evidence["host_receipts"] == []


@pytest.mark.parametrize(
    "mutation",
    [
        "foreign-question",
        "foreign-source",
        "foreign-profile",
        "foreign-runtime",
        "missing-physical",
        "wrong-scatter",
        "invented-reply",
        "unknown-reason",
        "not-limited",
        "false-limit",
        "no-excess",
    ],
)
def test_limitation_classification_requires_actual_closed_member_correspondence(
    controlled, mutation
):
    case = copy.deepcopy(controlled)
    if mutation == "foreign-question":
        payload = case.request.payload
        payload["questions"] = dict(reversed(tuple(payload["questions"].items())))
        case.request = replace(case.request, content=ordered_native_bytes(payload))
    elif mutation == "foreign-source":
        case.pin = {**case.pin, "source_product": "foreign"}
    elif mutation == "foreign-profile":
        case.selection.native.fingerprint = "0" * 64
    elif mutation == "foreign-runtime":
        case.selection.runtime = b"other"
    elif mutation == "missing-physical":
        case.reply = replace(
            case.reply, execution_receipt=replace(case.reply.execution_receipt, physical=())
        )
    elif mutation == "wrong-scatter":
        case.reply = replace(
            case.reply, execution_receipt=replace(case.reply.execution_receipt, member_offset=1)
        )
    elif mutation == "invented-reply":
        case.native["private_note"] = "must not escape through diagnostics"
    elif mutation == "unknown-reason":
        case.native["reason"] = "some-provider-string"
    elif mutation == "false-limit":
        case.native["limit"] = True
    elif mutation == "no-excess":
        case.native["row_tokens"] = [4096]
    else:
        case.native["outcome"] = "failed"
        assert classify(case) is None
        return
    with pytest.raises(ValueError):
        classify(case)


@pytest.mark.parametrize("field", ["request_id", "generation", "task_id", "attempt"])
def test_batched_failure_never_attributes_another_attempt_diagnostic(controlled, field):
    limited = classify(controlled)
    assert limited is not None
    other = {**controlled.fence, field: "other" if field == "request_id" else 99}
    assert (
        known_d1_failure(
            ExceptionGroup("batch", [ValueError("other"), limited]),
            fence=wire_attempt_fence(other),
            runtime_id="runtime:one",
        )
        is None
    )
    selected = known_d1_failure(
        ExceptionGroup("batch", [ValueError("protected exception text"), limited]),
        fence=controlled.fence,
        runtime_id="runtime:one",
    )
    assert selected is not None
    assert selected["code"] == "d1-known-limitation"
    assert "protected exception text" not in json.dumps(selected)


@pytest.mark.parametrize(
    "mutation",
    [
        "extra",
        "standing",
        "emitted",
        "missing-pin",
        "missing-receipt",
        "unconfirmed",
        "cpu-reply",
        "empty-physical-evidence",
    ],
)
def test_native_attempt_wire_preserves_closed_unperformed_diagnostic(controlled, mutation):
    limited = classify(controlled)
    assert limited is not None
    typed_failure = known_d1_failure(limited, fence=controlled.fence, runtime_id="runtime:one")
    assert typed_failure is not None
    # Malformations are untrusted external JSON, not values of the checked DTO.
    failure = json.loads(json.dumps(typed_failure))
    request = {**controlled.fence, "physical_retirement": "confirmed", "failure": failure}
    assert validate_native_wire("release_data_attempt", "input", request) == request
    diagnostic = failure["d1_limitation"]
    if mutation == "extra":
        diagnostic["native_reply"]["untyped"] = {}
    elif mutation == "standing":
        diagnostic["standing"] = "private_uncalibrated_candidates"
    elif mutation == "emitted":
        diagnostic["emitted_count"] = 1
    elif mutation == "missing-pin":
        del diagnostic["source_pin"]
    elif mutation == "missing-receipt":
        del diagnostic["execution_evidence"]
    elif mutation == "cpu-reply":
        diagnostic["execution_evidence"]["cpu_replies"] = ["untyped data"]
    elif mutation == "empty-physical-evidence":
        diagnostic["execution_evidence"]["provider_receipts"] = []
    else:
        request["physical_retirement"] = "unknown"
    with pytest.raises(ValueError):
        validate_native_wire("release_data_attempt", "input", request)


def test_known_failure_uses_existing_release_only_after_claim_check(controlled):
    from corpus_structure.orchestrate import data_operations

    retained = []
    executor = object.__new__(data_operations.NativeDemandExecutor)
    executor._draft_origins = {}
    checked = []
    calls = SimpleNamespace(release_data_attempt=retained.append)
    owner = SimpleNamespace(check_claim=checked.append, settle=lambda claim, action: action(calls))
    claim = SimpleNamespace(
        fence=controlled.fence,
        runtime_id="runtime:one",
        task_id=controlled.fence["task_id"],
        attempt=controlled.fence["attempt"],
    )
    executor._known_failure(claim, owner, classify(controlled), phase="computation")
    assert checked == [claim]
    assert retained[0]["physical_retirement"] == "confirmed"
    assert retained[0]["failure"]["d1_limitation"]["native_reply"]["reason"] == "packed_row_tokens"
    executor._known_failure(claim, owner, ValueError("protected content"), phase="computation")
    assert retained[1]["failure"] == {
        "code": "builtins.ValueError",
        "message": "computation did not complete",
    }


def test_read_only_undisclosed_diagnostic_keeps_authorized_failure_metadata(controlled):
    output = wire_contracts()["read_demand_result"]["output"]
    schema = {
        "$ref": "#/definitions/attempt_failure_observation",
        "definitions": output["definitions"],
    }
    failure: dict[str, Any] = dict(
        code="d1-known-limitation",
        message="native D1 question inspection was limited",
        d1_limitation_disclosure="undisclosed",
    )
    row = dict(
        failure_id="failure:one",
        **{key: value for key, value in controlled.fence.items()},
        failure=failure,
    )
    validate_wire_schema(schema, row)
    # The output projection flag cannot be submitted as an authored failure.
    with pytest.raises(ValueError):
        validate_native_wire(
            "release_data_attempt",
            "input",
            dict(**controlled.fence, physical_retirement="confirmed", failure=failure),
        )
    limited = classify(controlled)
    assert limited is not None
    typed_failure = known_d1_failure(limited, fence=controlled.fence, runtime_id="runtime:one")
    assert typed_failure is not None
    failure["d1_limitation"] = typed_failure["d1_limitation"]
    with pytest.raises(ValueError):
        validate_wire_schema(schema, row)
