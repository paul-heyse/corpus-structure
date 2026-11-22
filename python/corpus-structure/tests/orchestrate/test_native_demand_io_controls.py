"""Public executor effects with authored wire replies and a forbidden SQL engine."""

import json
from dataclasses import replace
from types import SimpleNamespace

import pytest
from orchestrate.executor_support import Active, execution_case, executor_preparation, policy_for
from semantic.data_operation_kernel_support import prepare_kernel
from semantic.external_scenarios import EXTERNAL

from corpus_structure.orchestrate.data_operations import NativeDemandExecutionError
from corpus_structure.semantic.claim_lifetime import ClaimSettlementUncertain
from corpus_structure.semantic.identity import canonical_bytes


def test_external_packet_custody_precedes_python_resolution(monkeypatch):
    preparation = prepare_kernel(EXTERNAL)
    operation = next(
        item.semantic_id for item in preparation.model.operations if item.external is not None
    )
    executor, observed = execution_case(
        monkeypatch,
        preparation.prepared,
        policy_for(preparation.prepared),
        (operation,),
        {},
    )
    calls = executor.native_io.calls
    events = []

    def retain_packet(payload):
        events.append(("packet-custody", payload["request_id"]))
        observed.live.remove(payload["request_id"])
        return dict(packet_id="packet:0", packet_digest="a" * 64, state="awaiting-external")

    def forbidden_resolution(*args, **options):
        events.append(("python-resolution", None))
        raise AssertionError("external packet custody must not acquire a Python capability")

    calls.replies["retain_external_data_packet"] = retain_packet
    executor.native_io.acquire_execution = forbidden_resolution
    executor.native_io.hydrate_inputs = forbidden_resolution
    result = executor.advance("controlled-demand")
    assert result.receipt_count == 0
    assert events == [("packet-custody", "0")]
    assert [name for name, _ in calls.calls] == [
        "claim_data_requests",
        "retain_external_data_packet",
    ]
    assert not observed.live and not observed.receipts and not observed.failures


@pytest.mark.parametrize("retained_at_claim", [True, False], ids=["retained", "changed-action"])
def test_uncertain_publication_reconciles_exact_intent_without_recomputation(
    monkeypatch, retained_at_claim
):
    preparation = executor_preparation()
    computations, durable = [], {}

    def scalar(value, **options):
        computations.append(value)
        if False:
            yield
        return value

    executor, observed = execution_case(
        monkeypatch,
        preparation.prepared,
        policy_for(preparation.prepared),
        ("scalar",),
        {"scalar": SimpleNamespace(native_selections=(), plan_python=scalar)},
    )
    calls = executor.native_io.calls
    publication_attempts, adoptions = [], []

    def publish(payload):
        publication_attempts.append(payload["intent_id"])
        replayed = payload["intent_id"] in durable
        durable[payload["intent_id"]] = "derivation:0"
        observed.live.discard("0")
        return dict(
            derivation_id="derivation:0",
            receipt_id="receipt:0",
            replayed=replayed,
            trust_snapshot={},
        )

    def adopt(payload):
        adoptions.append(payload["intent_id"])
        return dict(intent_id=payload["intent_id"], producer_task_id=1, producer_attempt=1)

    class UncertainPublication(Active):
        def settle(self, claim, callback):
            callback(self.calls)
            uncertainty = ClaimSettlementUncertain(claim, claim.holder, "0")
            self.uncertain[claim.request_id] = uncertainty
            raise uncertainty

    calls.replies.update(publish_data_derivation=publish, adopt_data_completion_intent=adopt)
    executor.native_io.owner = UncertainPublication(calls)
    with pytest.raises(NativeDemandExecutionError) as caught:
        executor.advance("controlled-demand")
    assert isinstance(caught.value.failures[0], ClaimSettlementUncertain)
    assert durable == {"0": "derivation:0"} and computations == [0]
    assert not observed.failures

    ready = executor._ready_items[0]
    executor._ready_items = (
        replace(
            ready,
            native=canonical_bytes(
                {
                    **json.loads(ready.native),
                    "release_id": "release:" + "a" * 64,
                    "runtime_id": "runtime:" + "b" * 64,
                    "action": "reconcile",
                    "retained_intent_id": "0",
                }
            ),
        ),
    )

    def forbidden_execution(*args, **options):
        raise AssertionError("retained reconciliation must not resolve or hydrate executable code")

    monkeypatch.setattr(executor, "_basis_context", forbidden_execution)
    monkeypatch.setattr(executor, "_hydrate", forbidden_execution)
    executor.native_io.owner = Active(calls)
    if not retained_at_claim:
        claim_reply = calls.replies["claim_data_requests"]

        def changed_action(payload):
            result = claim_reply(payload)
            claimed = result["items"][0]["result"]
            claimed["action"] = "compute"
            claimed["retained_intent_id"] = None
            return result

        calls.replies["claim_data_requests"] = changed_action
        with pytest.raises(NativeDemandExecutionError) as caught:
            executor.advance("controlled-demand")
        assert "native reconciliation claim no longer has a retained intent" in str(
            caught.value.failures[0]
        )
        assert publication_attempts == ["0"] and not adoptions
        assert computations == [0] and not observed.live and len(observed.failures) == 1
        return

    result = executor.advance("controlled-demand")
    assert result.receipt_count == 1
    assert json.loads(result.receipts[0])["replayed"] is True
    assert durable == {"0": "derivation:0"} and computations == [0]
    assert publication_attempts == ["0", "0"] and adoptions == ["0"]
    assert [name for name, _ in calls.calls].count("retain_data_completion_intent") == 1
    assert not observed.live and not observed.failures


def test_authored_claim_reply_missing_lease_is_rejected_at_wire_boundary(monkeypatch):
    preparation = executor_preparation()
    executor, _ = execution_case(
        monkeypatch,
        preparation.prepared,
        policy_for(preparation.prepared),
        ("scalar",),
        {"scalar": SimpleNamespace(native_selections=())},
    )
    calls = executor.native_io.calls
    reply = calls.replies["claim_data_requests"]

    def missing_lease(payload):
        result = reply(payload)
        del result["items"][0]["result"]["lease_until"]
        return result

    calls.replies["claim_data_requests"] = missing_lease
    with pytest.raises(NativeDemandExecutionError) as caught:
        executor.advance("controlled-demand")
    from jsonschema.exceptions import ValidationError

    error = caught.value.failures[0]
    assert isinstance(error, ValueError) and "native wire violates schema" in str(error)
    assert isinstance(error.__cause__, ValidationError)
    pending = [error.__cause__]
    messages = []
    while pending:
        current = pending.pop()
        messages.append(current.message)
        pending.extend(current.context)
    assert "'lease_until' is a required property" in messages


def test_named_fulfilled_use_advances_only_its_routed_hydrated_request(monkeypatch):
    from corpus_structure.orchestrate.data_operations import NamedFulfilledUse
    from corpus_structure.semantic.data_operation_service import NamedDemandSelection

    preparation = executor_preparation()
    computations, hydration, routed = [], [], []

    def scalar(value, **options):
        computations.append(value)
        if False:
            yield
        return value

    executor, observed = execution_case(
        monkeypatch,
        preparation.prepared,
        policy_for(preparation.prepared),
        ("scalar", "scalar"),
        {"scalar": SimpleNamespace(native_selections=(), plan_python=scalar)},
    )
    planner = executor.native_io.planner(executor.model)
    page = {
        **planner.resume("controlled-demand"),
        "project_id": "controlled-project",
        "read_id": "controlled-read",
        "obligations": [
            {"obligation_id": "0", "operation_id": "scalar"},
            {"obligation_id": "1", "operation_id": "scalar"},
        ],
        "uses": [
            {
                "obligation_id": "0",
                "fate": "fulfilled",
                "derivation_id": "derivation:0",
                "products": [{"role": "result", "product_id": "product:0"}],
            }
        ],
        "intent": {
            "discovery": [
                {"producer": "scalar", "output_role": "result", "population": "unrelated"}
            ],
        },
    }
    origin = NamedFulfilledUse(
        NamedDemandSelection("controlled-project", "governed", "controlled-demand", 3),
        "use:origin",
    )
    authorization = b'{"caller":"approved"}'

    def route(snapshot, **options):
        assert snapshot is page
        routed.append(options)
        return (executor._ready_items[1],), ()

    def forbidden(*_args, **_options):
        pytest.fail("named advance expanded discovery or bound the unfiltered page")

    planner.resume = lambda *_args, **_options: page
    planner.ready_for_fulfilled_use = route
    planner.ready = planner.expand_discovery = forbidden
    executor.native_io.plan = lambda _model: planner
    hydrate = executor.native_io.hydrate_inputs

    def observe_hydration(model, selected, **options):
        hydration.append(selected.subject)
        return hydrate(model, selected, **options)

    executor.native_io.hydrate_inputs = observe_hydration
    result = executor.advance(
        "controlled-demand", authorization=authorization, fulfilled_use=origin
    )
    assert routed == [
        {
            "selection_name": "governed",
            "selection_generation": 3,
            "use_id": "use:origin",
            "authorization": authorization,
        }
    ]
    assert observed.claim_sets == [("1",)]
    assert hydration == ["1"]
    assert computations == [1] and observed.receipts == [("1", 1)]
    assert result.receipt_count == 1
