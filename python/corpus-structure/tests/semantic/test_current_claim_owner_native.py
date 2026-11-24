"""Actual current request custody through the shared physical claim owner.

The declared native storage kernel supplies controlled protocol values. These
controls claim no provider execution or scientific evidence from those values.
"""

from contextlib import contextmanager
from threading import Event
from typing import cast

import psycopg
import pytest
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError

from corpus_structure.orchestrate.data_operations import NativeRequestClaim
from corpus_structure.semantic._data_operation_wire import (
    WirePublishDataDerivationRequest,
    WireReadDemandResultRequest,
    WireRenewDataRequestRequest,
    WireRetainDataCompletionIntentRequest,
    WireRevokeDataSupportRequest,
)
from corpus_structure.semantic.claim_lifetime import (
    ClaimFenceLost,
    ClaimOwner,
    ClaimSettlementUncertain,
    DatabaseSettings,
    maintained_claims,
)
from corpus_structure.semantic.data_operation_storage import DataOperationStorage
from semantic.data_operation_demand_support import attach, claim, publish, retain
from semantic.data_operation_kernel_support import STORAGE

pytestmark = pytest.mark.parametrize("ddo_kernel", [STORAGE], indirect=True, ids=["storage"])


def acquired(kernel):
    _, _, _, request = attach(kernel)
    fence = claim(kernel, request, holder="owner")
    with kernel["engine"].connect() as connection:
        deadline = connection.scalar(
            text("SELECT lease_until FROM ops.task WHERE id=:id"), {"id": fence["task_id"]}
        )
    owned = NativeRequestClaim(
        **fence,
        release_id=kernel["prepared"].release_id,
        deadline=deadline,
        runtime_id=kernel["runtime"],
    )
    intent = retain(kernel, fence)

    def publish(connection):
        return DataOperationStorage(connection).publish_data_derivation(
            cast(
                WirePublishDataDerivationRequest, {**owned.fence, "intent_id": intent["intent_id"]}
            )
        )

    return owned, intent, publish


class LostCommitResponses:
    """Lose delivery after actual commits, retaining their real native receipts."""

    def __init__(self, engine, remaining):
        self.engine, self.remaining = engine, remaining

    @contextmanager
    def connect(self):
        with self.engine.connect() as connection:
            owner = self

            class Connection:
                @contextmanager
                def begin(self):
                    with connection.begin():
                        yield
                    if owner.remaining:
                        owner.remaining -= 1
                        raise psycopg.OperationalError("actual commit response lost")

                def __getattr__(self, name):
                    return getattr(connection, name)

            yield Connection()


def test_current_dynamic_owner_renews_retains_and_publishes_exact_native_request(ddo_kernel):
    owned, intent, publish = acquired(ddo_kernel)
    renewed = Event()

    def renew(connection, selected):
        result = DataOperationStorage(connection).renew_data_request(
            cast(WireRenewDataRequestRequest, {**selected.fence, "lease_seconds": 30})
        )
        if result["state"] == "lost":
            raise ClaimFenceLost(selected, result["reason"])
        renewed.set()

    with ddo_kernel["engine"].connect() as connection:
        completion = connection.scalar(
            text("SELECT payload FROM ops.data_completion_intent WHERE id=:id"),
            {"id": intent["intent_id"]},
        )

    def retain_exact(connection):
        return DataOperationStorage(connection).retain_data_completion_intent(
            cast(
                WireRetainDataCompletionIntentRequest,
                {**owned.fence, "runtime_id": ddo_kernel["runtime"], "completion": completion},
            )
        )

    with maintained_claims(ddo_kernel["engine"], (), "owner", interval=0.01, renew=renew) as owner:
        owner.add_claim(owned)
        assert renewed.wait(10)
        retained = owner.retain(owned, retain_exact)
        assert isinstance(retained, dict)
        assert retained["intent_id"] == intent["intent_id"]
        owner.check_claim(owned)
        published = owner.settle(owned, publish)
        assert isinstance(published, dict)
        assert published["derivation_id"]
        assert not owner.active


def test_selected_cut_allows_lease_renewal_but_still_fences_revocation(ddo_kernel):
    # A genuine published sibling makes this runtime a valid withdrawal target.
    _, _, _, sibling = attach(ddo_kernel, subject="published:renewal-control")
    sibling_fence = claim(ddo_kernel, sibling)
    publish(ddo_kernel, sibling_fence, retain(ddo_kernel, sibling_fence))
    demand, _, _, attached = attach(ddo_kernel, subject="live:renewal-control")
    fence = claim(ddo_kernel, attached, seconds=120)
    withdrawal = cast(
        WireRevokeDataSupportRequest,
        dict(
            project_id="ddo-test",
            original_source="source:test",
            selector_kind="runtime",
            selector=ddo_kernel["runtime"],
            reason="actual renewal/cut withdrawal control",
        ),
    )
    with ddo_kernel["engine"].begin() as reader:
        cut = DataOperationStorage(reader).read_demand_result(
            cast(WireReadDemandResultRequest, {"demand_id": demand["demand_id"], "limit": 1})
        )
        expected_scope = reader.scalar(text("SELECT ops.ddo_scope('ddo-test','source:test')"))
        assert cut["trust_snapshot"] == {expected_scope: 0}
        with ddo_kernel["engine"].begin() as renewal:
            renewal.exec_driver_sql("SET LOCAL lock_timeout='500ms'")
            renewed = DataOperationStorage(renewal).renew_data_request(
                cast(WireRenewDataRequestRequest, {**fence, "lease_seconds": 120})
            )
        assert renewed["state"] == "renewed"
        assert renewed["trust_snapshot"] == cut["trust_snapshot"]
        # Withdrawal must wait for the actual selected-cut trust locks.
        with pytest.raises(DBAPIError) as blocked, ddo_kernel["engine"].begin() as revoker:
            revoker.exec_driver_sql("SET LOCAL lock_timeout='100ms'")
            DataOperationStorage(revoker).revoke_data_support(withdrawal)
        assert isinstance(blocked.value.orig, psycopg.errors.LockNotAvailable)
    with ddo_kernel["engine"].begin() as revoker:
        DataOperationStorage(revoker).revoke_data_support(withdrawal)
    with ddo_kernel["engine"].begin() as renewal:
        lost = DataOperationStorage(renewal).renew_data_request(
            cast(WireRenewDataRequestRequest, {**fence, "lease_seconds": 120})
        )
        assert lost == {**fence, "state": "lost", "reason": "revoked"}
        stale = DataOperationStorage(renewal).renew_data_request(
            cast(
                WireRenewDataRequestRequest,
                {**fence, "holder": "stale-holder", "lease_seconds": 120},
            )
        )
        assert stale == {**fence, "holder": "stale-holder", "state": "lost", "reason": "fence"}


def test_current_lost_commit_response_replays_one_real_publication_before_retiring(ddo_kernel):
    owned, _, publish = acquired(ddo_kernel)
    engine = LostCommitResponses(ddo_kernel["engine"], 1)
    owner = ClaimOwner(engine, (owned,), "owner", DatabaseSettings(), lambda: None)
    published = owner.settle(owned, publish)
    assert isinstance(published, dict)
    assert published["replayed"] is True
    assert not owner.active and not owner.uncertain
    with ddo_kernel["engine"].connect() as connection:
        assert (
            connection.scalar(
                text("SELECT count(*) FROM ops.data_derivation WHERE request_id=:id"),
                {"id": owned.request_id},
            )
            == 1
        )


def test_current_uncertain_publication_keeps_exact_callback_and_recovers_native_receipt(ddo_kernel):
    owned, _, publish = acquired(ddo_kernel)
    engine = LostCommitResponses(ddo_kernel["engine"], 2)
    owner = ClaimOwner(engine, (owned,), "owner", DatabaseSettings(), lambda: None)
    with pytest.raises(ClaimSettlementUncertain) as refused:
        owner.settle(owned, publish)
    assert refused.value.completion is publish and refused.value.retire is True
    assert owner.active and owner.uncertain
    with pytest.raises(ClaimSettlementUncertain) as changed:
        owner.settle(owned, lambda connection: publish(connection))
    assert changed.value is refused.value
    published = owner.settle(owned, publish)
    assert isinstance(published, dict)
    assert published["replayed"] is True
    assert not owner.active and not owner.uncertain
    with ddo_kernel["engine"].connect() as connection:
        assert (
            connection.scalar(
                text("SELECT count(*) FROM ops.data_derivation WHERE request_id=:id"),
                {"id": owned.request_id},
            )
            == 1
        )


def test_retained_upload_stop_interrupts_its_live_transaction_and_releases_borrower(ddo_kernel):
    from concurrent.futures import ThreadPoolExecutor
    from contextvars import copy_context

    from corpus_structure.core.execution_control import ExecutionStopRequest, execution_stop_scope
    from corpus_structure.orchestrate.native_demand_io import NativeDemandClaims

    owned, _, _ = acquired(ddo_kernel)
    owner = ClaimOwner(ddo_kernel["engine"], (owned,), "owner", DatabaseSettings(), lambda: None)
    claims = NativeDemandClaims(owner)
    entered = Event()
    stop = ExecutionStopRequest()

    def blocked(calls):
        entered.set()
        calls.connection.execute(text("SELECT pg_sleep(30)"))
        pytest.fail("managed cancellation must interrupt the live database borrower")

    with execution_stop_scope(stop):
        context = copy_context()
        with ThreadPoolExecutor(max_workers=1) as executor:
            future = executor.submit(
                context.run, claims.retain, owned, blocked, cancel_on_stop=True
            )
            assert entered.wait(10)
            stop.requested.set()
            with pytest.raises(DBAPIError) as stopped:
                future.result(timeout=10)
            assert getattr(stopped.value.orig, "sqlstate", None) == "57014"
    assert stop.draining.is_set()
    # This checkout succeeds after the cancelled borrower's registration has retired.
    with ddo_kernel["engine"].begin() as connection:
        assert connection.scalar(text("SELECT 1")) == 1
    assert owner.active and not owner.uncertain
