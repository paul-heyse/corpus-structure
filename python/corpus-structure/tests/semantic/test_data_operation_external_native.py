"""Real external packet/task/receipt/publication custody; agents are never auto-called."""

import pytest
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError

from corpus_structure.semantic.data_operation_external import ExternalDataSession
from corpus_structure.semantic.data_operation_storage import DataOperationStorage
from semantic.data_operation_demand_support import attach, claim
from semantic.external_scenarios import EXTERNAL

pytestmark = pytest.mark.parametrize("ddo_kernel", [EXTERNAL], indirect=True, ids=["external"])
RESULT = {"outcome": "success", "outputs": [{"role": "result", "body": 7}]}


def packet(kernel, *, max_bytes=100000, subject="subject:one"):
    demand, _, _, attached = attach(kernel, subject=subject)
    fence = claim(kernel, attached)
    with kernel["engine"].begin() as connection:
        retained = DataOperationStorage(connection).retain_external_data_packet({**fence, "runtime_id": kernel["runtime"], "max_bytes": max_bytes})
    return demand, attached, fence, retained


def test_external_packet_waits_without_fulfillment_then_publishes_real_native_receipt(ddo_kernel):
    demand, attached, producer, retained = packet(ddo_kernel)
    session = ExternalDataSession(ddo_kernel["engine"], "ddo-test", demand_id=demand["demand_id"])
    headers = session.queue()["packets"]
    assert len(headers) == 1 and headers[0]["packet_id"] == retained["packet_id"]
    with ddo_kernel["engine"].begin() as connection:
        storage = DataOperationStorage(connection)
        snapshot = storage.read_demand_result({"demand_id": demand["demand_id"]})
        assert any(use["fate"] == "awaiting-external" for use in snapshot["uses"])
        assert all(not use["products"] for use in snapshot["uses"])
        assert (
            storage.claim_data_request({"request_id": attached["request_id"], "holder": "ordinary", "lease_seconds": 30})["state"]
            == "no-work"
        )
    leased = session.claim(retained["packet_id"])
    assert leased["attempt"] == producer["attempt"] + 1 and leased["action"] == "compute"
    body = session.read(retained["packet_id"], leased)
    assert body["packet_digest"] == retained["packet_digest"]
    assert body["packet"]["inputs"] == []
    assert body["packet"]["protocol"]["reference_scope"] == "declared-inputs-only"
    assert body["packet"]["result_contract"][0]["schema"]["type"] == "integer"
    completed = session.submit(
        retained["packet_id"],
        leased,
        RESULT,
        actor_assertion="controlled-external",
        model_assertion=None,
    )
    assert completed["state"] == "committed"
    receipt = completed["receipt"]
    with ddo_kernel["engine"].connect() as connection:
        assert receipt["admitting_principal"] == connection.scalar(text("SELECT SESSION_USER"))
    assert (
        receipt["actor_assertion"] == "controlled-external" and receipt["model_assertion"] is None
    )
    assert receipt["task_id"] == leased["task_id"] and receipt["attempt"] == leased["attempt"]
    inspected = session.inspect(retained["packet_id"])
    assert inspected["state"] == "committed" and inspected["receipt"] == receipt
    # Replay after terminal publication resolves custody rather than redoing work.
    assert (
        session.submit(
            retained["packet_id"],
            leased,
            RESULT,
            actor_assertion="controlled-external",
            model_assertion=None,
        )["receipt"]
        == receipt
    )
    assert session.queue()["packets"] == []


def test_external_release_takeover_fences_old_producer_and_assertions(ddo_kernel):
    _, _, _, retained = packet(ddo_kernel)
    first = ExternalDataSession(ddo_kernel["engine"], "ddo-test")
    old = first.claim(retained["packet_id"])
    first.release(retained["packet_id"], old, reason="external owner relinquished")
    second = ExternalDataSession(ddo_kernel["engine"], "ddo-test")
    new = second.claim(retained["packet_id"])
    assert new["attempt"] == old["attempt"] + 1
    with pytest.raises(DBAPIError, match=r"fence|claim|attempt|lease"):
        first.read(retained["packet_id"], old)
    with pytest.raises(DBAPIError, match="assertion"):
        second.submit(
            retained["packet_id"], new, RESULT, actor_assertion="invented", model_assertion=None
        )
    assert second.inspect(retained["packet_id"])["state"] == "awaiting-external"
    second.submit(
        retained["packet_id"],
        new,
        RESULT,
        actor_assertion="controlled-external",
        model_assertion=None,
    )
    with pytest.raises(DBAPIError, match="different immutable"):
        second.submit(
            retained["packet_id"],
            new,
            {"outcome": "success", "outputs": [{"role": "result", "body": 8}]},
            actor_assertion="controlled-external",
            model_assertion=None,
        )


def test_external_packet_byte_limit_and_cancellation_do_not_publish(ddo_kernel):
    demand, _, _, attached = attach(ddo_kernel)
    fence = claim(ddo_kernel, attached)
    with pytest.raises(DBAPIError, match="capacity"), ddo_kernel["engine"].begin() as connection:
        DataOperationStorage(connection).retain_external_data_packet({**fence, "runtime_id": ddo_kernel["runtime"], "max_bytes": 1})
    with ddo_kernel["engine"].begin() as connection:
        retained = DataOperationStorage(connection).retain_external_data_packet({**fence, "runtime_id": ddo_kernel["runtime"], "max_bytes": 100000})
    session = ExternalDataSession(ddo_kernel["engine"], "ddo-test")
    leased = session.claim(retained["packet_id"])
    with ddo_kernel["engine"].begin() as connection:
        DataOperationStorage(connection).cancel_data_demand({"demand_id": demand["demand_id"], "reason": "cancel exact external interest"})
    with pytest.raises(DBAPIError):
        session.submit(
            retained["packet_id"],
            leased,
            RESULT,
            actor_assertion="controlled-external",
            model_assertion=None,
        )
    assert session.inspect(retained["packet_id"])["state"] in {"cancelled", "superseded"}
    assert session.queue()["packets"] == []


def test_ordinary_executor_hands_off_external_command_without_python_port(ddo_kernel):
    from corpus_structure.orchestrate.data_operations import NativeDemandExecutor
    from corpus_structure.semantic.python_operation_sources import PythonSourceCollection

    demand, _, _, _ = attach(ddo_kernel)
    executor = NativeDemandExecutor(
        ddo_kernel["engine"],
        ddo_kernel["prepared"],
        ddo_kernel.preparation.runtime,
        PythonSourceCollection(()),
        schema=ddo_kernel.preparation.bundle,
    )
    result = executor.advance(demand["demand_id"])
    assert result.receipt_count == 0 and result.receipts == ()
    assert executor.ports == {} and executor.budget.used_bytes == 0
    session = ExternalDataSession(ddo_kernel["engine"], "ddo-test")
    headers = session.queue()["packets"]
    assert len(headers) == 1 and headers[0]["state"] == "awaiting-external"
    assert executor.advance(demand["demand_id"]).receipt_count == 0


def test_retained_external_result_is_adopted_without_repeating_actor_work(ddo_kernel):
    from corpus_structure.semantic.data_operation_external import ExternalResultPort
    from corpus_structure.semantic.data_operation_json import json_bytes

    _, _, _, retained = packet(ddo_kernel)
    session = ExternalDataSession(ddo_kernel["engine"], "ddo-test")
    first = session.claim(retained["packet_id"], lease_seconds=30)
    actual = session.read(retained["packet_id"], first)["packet"]
    completion = ExternalResultPort(json_bytes(actual), ddo_kernel["model"], 100000).completion(
        RESULT
    )
    with ddo_kernel["engine"].begin() as connection:
        admitted = DataOperationStorage(connection).admit_external_data_result({
                "packet_id": retained["packet_id"],
                **{
                    name: first[name]
                    for name in ("request_id", "generation", "task_id", "attempt", "holder")
                },
                "actor_assertion": "controlled-external",
                "model_assertion": None,
                "completion": completion,
            })
        released = DataOperationStorage(connection).release_data_attempt({
                **{
                    name: first[name]
                    for name in ("request_id", "generation", "task_id", "attempt", "holder")
                },
                "physical_retirement": "confirmed",
                "failure": {
                    "code": "controlled-actor-retired",
                    "message": "Actor work finished; publication owner retired before acknowledgement.",
                },
            })
        assert (
            released["state"] == "released"
            and released["retained_intent_id"] == admitted["intent_id"]
        )
    successor = ExternalDataSession(ddo_kernel["engine"], "ddo-test")
    second = successor.claim(retained["packet_id"])
    assert second["action"] == "reconcile" and second["retained_intent_id"] == admitted["intent_id"]
    completed = successor.reconcile(retained["packet_id"], second)
    assert completed["state"] == "committed" and completed["receipt"] == admitted["receipt"]
    assert completed["receipt"]["attempt"] == first["attempt"] < second["attempt"]


def test_external_lost_publication_ack_is_inspected_without_reexecution(ddo_kernel, monkeypatch):
    _, _, _, retained = packet(ddo_kernel)
    session = ExternalDataSession(ddo_kernel["engine"], "ddo-test")
    fence = session.claim(retained["packet_id"])
    invoke = session._invoke
    publications = []

    def lost_ack(operation, payload, **options):
        actual = invoke(operation, payload, **options)
        if operation == "publish_data_derivation":
            publications.append(actual)
            raise DBAPIError(
                None,
                None,
                RuntimeError("controlled lost committed acknowledgement"),
                connection_invalidated=True,
            )
        return actual

    monkeypatch.setattr(session, "_invoke", lost_ack)
    completed = session.submit(
        retained["packet_id"],
        fence,
        RESULT,
        actor_assertion="controlled-external",
        model_assertion=None,
    )
    assert completed["state"] == "committed" and len(publications) == 1
    assert completed["publication"]["derivation_id"] == publications[0]["derivation_id"]


def test_external_current_runtime_distrust_refuses_new_result_but_keeps_exact_receipt_replay(
    ddo_kernel,
):
    _, _, _, first_packet = packet(ddo_kernel)
    session = ExternalDataSession(ddo_kernel["engine"], "ddo-test")
    first = session.claim(first_packet["packet_id"])
    completed = session.submit(
        first_packet["packet_id"],
        first,
        RESULT,
        actor_assertion="controlled-external",
        model_assertion=None,
    )
    _, _, _, second_packet = packet(ddo_kernel, subject="subject:two")
    second = session.claim(second_packet["packet_id"])
    with ddo_kernel["engine"].begin() as connection:
        DataOperationStorage(connection).revoke_data_support({
                "project_id": "ddo-test",
                "original_source": "source:test",
                "selector_kind": "runtime",
                "selector": ddo_kernel["runtime"],
                "reason": "withdraw external runtime after independent first publication",
            })
    with pytest.raises(DBAPIError, match="revoked"):
        session.submit(
            second_packet["packet_id"],
            second,
            RESULT,
            actor_assertion="controlled-external",
            model_assertion=None,
        )
    assert session.queue()["packets"] == []
    replay = session.submit(
        first_packet["packet_id"],
        first,
        RESULT,
        actor_assertion="controlled-external",
        model_assertion=None,
    )
    assert replay["receipt"] == completed["receipt"] and replay["state"] == "committed"


def test_native_product_page_preflights_body_and_bounds_complete_envelope_without_charging_frontier(
    ddo_kernel,
):
    demand, _, _, retained = packet(ddo_kernel)
    session = ExternalDataSession(ddo_kernel["engine"], "ddo-test")
    fence = session.claim(retained["packet_id"])
    session.submit(
        retained["packet_id"],
        fence,
        RESULT,
        actor_assertion="controlled-external",
        model_assertion=None,
    )
    with ddo_kernel["engine"].begin() as connection:
        native = DataOperationStorage(connection)
        frontier = native.read_demand_result({"demand_id": demand["demand_id"], "max_bytes": 1})
        assert (
            frontier["view"] == "frontier"
            and frontier["uses"][0]["products"][0]["body_state"] == "not_requested"
        )
    for bound, reason in (
        (1, "product page exceeds max_bytes"),
        (64, "page envelope exceeds max_bytes"),
    ):
        with pytest.raises(DBAPIError, match=reason), ddo_kernel["engine"].begin() as connection:
            DataOperationStorage(connection).read_demand_result({"demand_id": demand["demand_id"], "view": "products", "max_bytes": bound})
    with ddo_kernel["engine"].begin() as connection:
        completed = DataOperationStorage(connection).read_demand_result({"demand_id": demand["demand_id"], "view": "products", "max_bytes": 100000})
    assert completed["uses"][0]["products"][0]["body"] == ["integer", "7"]
