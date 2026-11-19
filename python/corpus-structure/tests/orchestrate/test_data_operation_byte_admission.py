"""Request admission shares actual retained CPU preparation and physical leases."""

import importlib
import inspect
import json
from concurrent.futures import Future
from threading import Event
from types import SimpleNamespace

import pytest
from orchestrate.executor_support import (
    execution_case,
    policy_for,
)
from orchestrate.executor_support import (
    prepared as prepared,
)

from corpus_structure.orchestrate import data_operations
from corpus_structure.semantic.cpu_execution import (
    CapacityExceeded,
    OwnedByteBudget,
    release_capsule,
)
from corpus_structure.semantic.data_operation_cpu import PythonCPUDescriptor, plan_cpu_call


@pytest.mark.parametrize("fail_first", [False, True])
def test_real_prepared_capsule_defers_second_request_and_preserves_siblings(
    tmp_path, monkeypatch, prepared, fail_first
):
    path = tmp_path / "admission_kernel.py"
    source = """from corpus_structure.semantic.types import PreparedRelease

def derive(value: int, fail_first: bool, prepared: PreparedRelease) -> int:
    prepared.validate_json('Thing', '{"id":"A"}')
    if fail_first and value == 0:
        raise ValueError('controlled first request failure')
    return value + 7
"""
    path.write_text(source)
    monkeypatch.syspath_prepend(str(tmp_path))
    # A fresh module name avoids reusing another parametrization's physical file.
    module = "admission_kernel_" + str(fail_first).lower()
    renamed = path.with_name(module + ".py")
    path.rename(renamed)
    function = importlib.import_module(module).derive
    signature = inspect.signature(function)
    descriptor = PythonCPUDescriptor(
        ((module, str(renamed), source.encode()),),
        module + ".derive",
        (),
        verification="prepared-kernel",
        prepared_parameter="prepared",
        prepared_release_id=prepared.release_id,
    )

    generations = []

    def plan(value, *, check_active, execution_owner, **_):
        generations.append(execution_owner.cpu)
        reply = yield from plan_cpu_call(
            descriptor,
            signature.bind(value, fail_first, prepared),
            signature,
            verify=lambda: None,
            execution_owner=execution_owner,
            check_active=check_active,
        )
        return json.loads(reply.content)

    port = SimpleNamespace(requires_prepared_schema=True, native_selections=(), plan_python=plan)
    policy = policy_for(prepared)
    executor, observed = execution_case(
        monkeypatch, prepared, policy, ("prepared",) * 3, {"prepared": port}
    )
    capsule_size = len(release_capsule(prepared))
    assert 0 < capsule_size < executor.reservation
    assert policy.max_owned_bytes == 2 * executor.reservation and policy.max_claims == 2
    if fail_first:
        with pytest.raises(data_operations.NativeDemandExecutionError) as caught:
            executor.advance("controlled-demand")
        assert caught.value.result.receipt_count == 2 and len(caught.value.failures) == 1
    else:
        assert executor.advance("controlled-demand").receipt_count == 3
    # Public invocation retires each actual CPU generation and its captured capsule.
    assert generations and all(generation.scope._physical_retired for generation in generations)
    assert [index for index, _ in observed.claims] == ["0", "1", "2"]
    assert all(
        capsule_size + executor.reservation <= used <= policy.max_owned_bytes
        for _, used in observed.claims
    )
    assert max(observed.windows) <= policy.max_claims
    assert dict(observed.receipts) == ({"1": 8, "2": 9} if fail_first else {"0": 7, "1": 8, "2": 9})
    assert not observed.live and executor.budget.used_bytes == 0


def test_batch_chunks_and_scalar_sibling_share_claim_and_byte_bounds(monkeypatch, prepared):
    batches = []

    def scalar(value, *, execution_owner, **_):
        (result,) = yield (
            data_operations.PreparedWork(lambda: execution_owner.submit_python(lambda: value)),
        )
        return result

    def batch(members, *, execution_owner, **_):
        batches.append(len(members))
        (result,) = yield (
            data_operations.PreparedWork(
                lambda: execution_owner.submit_python(
                    lambda: SimpleNamespace(members=tuple((m.member, m.values) for m in members))
                )
            ),
        )
        return result

    ports = {
        "scalar": SimpleNamespace(native_selections=(), plan_python=scalar),
        "batch": SimpleNamespace(native_selections=(), plan_batch_python=batch),
    }
    executor, observed = execution_case(
        monkeypatch,
        prepared,
        policy_for(prepared, credits=4),
        ("batch",) * 5 + ("scalar",),
        ports,
    )
    result = executor.advance("controlled-demand")
    assert result.receipt_count == 6
    assert sum(batches) == 5 and max(batches) <= 2 and len(batches) >= 3
    assert max(observed.windows) <= 2
    assert all(used <= executor.policy.max_owned_bytes for _, used in observed.claims)
    assert executor.budget.used_bytes == 0


def test_preparation_that_cannot_hold_one_request_refuses_before_claim(monkeypatch, prepared):
    policy = policy_for(prepared, credits=1)
    port = SimpleNamespace(native_selections=(), requires_prepared_schema=True)
    executor, observed = execution_case(
        monkeypatch, prepared, policy, ("prepared",), {"prepared": port}
    )
    with pytest.raises(data_operations.NativeDemandExecutionError) as caught:
        executor.advance("controlled-demand")
    (failure,) = caught.value.failures
    assert isinstance(failure, CapacityExceeded)
    assert "preparation and one complete request" in str(failure)
    assert not observed.claims and executor.budget.used_bytes == 0


def test_reduced_credit_allows_progress_while_an_old_physical_share_retires(monkeypatch, prepared):
    third_started = Event()
    retired = Future()

    class RetiringWork:
        def __init__(self, reservation):
            self.share = reservation.share()
            self.reply = Future()
            self.reply.set_result(0)
            self.collected = False

        @property
        def future(self):
            return retired if self.collected else self.reply

        def collect(self):
            self.collected = True
            return self.reply.result()

        def cancel(self):
            retired.cancel()

        def retire(self):
            if not retired.done():
                return False
            self.share.release()
            return True

    def plan(value, *, execution_owner, **_):
        def compute():
            if value == 1:
                assert third_started.wait(5), "reduced credit never admitted the next request"
                retired.set_result(None)
            if value == 2:
                third_started.set()
            return value

        (result,) = yield (
            data_operations.PreparedWork(
                lambda: (
                    RetiringWork(execution_owner.reservation)
                    if value == 0
                    else execution_owner.submit_python(compute)
                )
            ),
        )
        return result

    executor, observed = execution_case(
        monkeypatch,
        prepared,
        policy_for(prepared),
        ("scalar",) * 3,
        {"scalar": SimpleNamespace(native_selections=(), plan_python=plan)},
    )
    result = executor.advance("controlled-demand")
    assert result.receipt_count == 3 and third_started.is_set()
    assert [index for index, _ in observed.claims] == ["0", "1", "2"]
    assert executor.budget.used_bytes == 0


def test_cancel_before_admitted_plan_starts_releases_its_credit(monkeypatch, prepared):
    executor, observed = execution_case(
        monkeypatch,
        prepared,
        policy_for(prepared),
        ("scalar",),
        {"scalar": SimpleNamespace(native_selections=())},
    )

    def cancel_after_admission(plan, _owner):
        frontier = next(plan)
        child = frontier.admit()
        assert executor.budget.used_bytes == executor.reservation
        child.close()  # An unstarted generator never runs its own finally block.
        plan.close()

    monkeypatch.setattr(data_operations, "drive_prepared_work", cancel_after_admission)
    executor.advance("controlled-demand")
    assert not observed.claims and executor.budget.used_bytes == 0


def test_atomic_budget_defers_until_last_physical_share_retires():
    budget = OwnedByteBudget(20)
    reservation = budget.try_admit(20)
    assert reservation is not None
    physical = reservation.share()
    reservation.release()
    assert budget.try_admit(20) is None and budget.used_bytes == 20
    physical.release()
    deferred = budget.try_admit(20)
    assert deferred is not None
    deferred.release()
    with pytest.raises(CapacityExceeded, match="complete request"):
        budget.try_admit(21)
    assert budget.used_bytes == 0


def test_stage_b_reduces_only_the_single_owned_charge():
    budget = OwnedByteBudget(100)
    reservation = budget.admit(100)
    reservation.reduce_to(35)
    assert reservation.size == budget.used_bytes == 35
    with pytest.raises(ValueError, match="cannot grow"):
        reservation.reduce_to(36)
    borrower = reservation.share()
    with pytest.raises(RuntimeError, match="shared"):
        reservation.reduce_to(20)
    reservation.release()
    assert budget.used_bytes == 35
    borrower.release()
    assert budget.used_bytes == 0
    with pytest.raises(RuntimeError, match="retired"):
        reservation.reduce_to(0)


def test_measured_batch_boundary_rehydrates_without_reclaiming(monkeypatch, prepared):
    import weakref

    batches, hydrations, references = [], [], {}

    def batch(members, *, execution_owner, **_):
        identifiers = tuple(str(member.values) for member in members)
        batches.append(identifiers)
        if identifiers == ("0",):
            # The overflowing member's decoded bodies have been discarded before
            # stage B and the current physical call; only its native claim stays.
            assert references["1"][0]() is None
            assert "1" not in execution_owner.consumer_inputs
        if False:
            yield
        return SimpleNamespace(
            members=tuple((member.member, str(member.values)) for member in members)
        )

    executor, observed = execution_case(
        monkeypatch,
        prepared,
        policy_for(prepared, max_claims=3, credits=2),
        ("batch",) * 3,
        {"batch": SimpleNamespace(native_selections=(), plan_batch_python=batch)},
    )

    def hydrate(model, selected, **options):
        from corpus_structure.semantic.data_operation_consumers import HydratedConsumerSelection

        identifier = selected.subject
        hydrations.append(identifier)
        body = HydratedConsumerSelection(
            selected,
            (),
            measured_bytes=executor.policy.max_packet_bytes // 2 + 1,
        )
        references.setdefault(identifier, []).append(weakref.ref(body))
        return body

    executor.native_io.hydrate_inputs = hydrate
    result = executor.advance("controlled-demand")
    assert result.receipt_count == 3
    assert [identifier for identifier, _ in observed.claims] == ["0", "1", "2"]
    assert hydrations == ["0", "1", "1", "2", "2"]
    assert batches == [("0",), ("1",), ("2",)]
    assert max(observed.windows) <= executor.policy.max_claims
    assert executor.budget.used_bytes == 0 and not observed.live


def test_one_frontier_replenishes_multiple_logical_pages(monkeypatch, prepared):
    prepared_pages, driver_calls = [], []

    def scalar(value, **_):
        if False:
            yield
        return value

    executor, observed = execution_case(
        monkeypatch,
        prepared,
        policy_for(prepared),
        ("scalar",) * 6,
        {"scalar": SimpleNamespace(native_selections=(), plan_python=scalar)},
    )

    planner = executor.native_io.plan(executor.model)

    def resume(demand, **options):
        index = options.get("after") or 0
        snapshot = dict(
            demand_id=demand,
            release_id=prepared.release_id,
            runtime_id=executor.runtime.runtime_id,
            state="active",
            obligations=[],
            uses=[],
            populations=[],
            intent={"discovery": []},
            selection={"version": "data-demand-intent-v2", "operations": [{"operation": "scalar"}]},
            control_page=index,
            continuation=None
            if index == 2
            else dict(selection={}, after=index + 1, trust_snapshot={}, read_id="controlled-read"),
        )
        return snapshot

    def ready(snapshot, **options):
        index = snapshot["control_page"]
        prepared_pages.append(index)
        return executor._ready_items[2 * index : 2 * index + 2]

    planner.resume, planner.ready = resume, ready
    executor.native_io.plan = lambda model: planner
    driver = data_operations.drive_prepared_work

    def drive(plan, owner):
        driver_calls.append(1)
        return driver(plan, owner)

    monkeypatch.setattr(data_operations, "drive_prepared_work", drive)
    result = executor.advance("controlled-demand")
    assert prepared_pages == [0, 1, 2] and driver_calls == [1]
    assert result.receipt_count == 6
    assert max(observed.windows) <= 2 and executor.budget.used_bytes == 0


def test_cold_preparation_defers_to_driver_ticks_without_failing_or_claiming_early(
    monkeypatch, prepared
):
    from corpus_structure.orchestrate.execution_host import ExecutionPreparationDeferred

    deferred = Event()
    calls = []

    def scalar(value, *, execution_owner, **_):
        def compute():
            if value == 0:
                assert deferred.wait(5), "cold preparation blocked the physical driver"
            return value

        (answer,) = yield (
            data_operations.PreparedWork(lambda: execution_owner.submit_python(compute)),
        )
        return answer

    executor, observed = execution_case(
        monkeypatch,
        prepared,
        policy_for(prepared),
        ("scalar",) * 2,
        {"scalar": SimpleNamespace(native_selections=(), plan_python=scalar)},
    )

    prepare_ready = executor._prepare_ready

    def prepare(item, authorization):
        calls.append(item.obligation)
        if item.obligation == "1" and not observed.receipts:
            assert not any(identifier == "1" for identifier, _ in observed.claims)
            deferred.set()
            raise ExecutionPreparationDeferred("previous physical reply remains owned")
        return prepare_ready(item, authorization)

    # Exercise the frontier's per-item defer protocol before a claim is acquired.
    executor._prepare_ready = prepare
    result = executor.advance("controlled-demand")
    assert deferred.is_set()
    assert dict(observed.receipts) == {"0": 0, "1": 1}
    assert result.receipt_count == 2 and len(calls) >= 2
    assert executor.budget.used_bytes == 0


@pytest.mark.parametrize("item_limit,byte_limit", [(2, 1000), (4, 5)])
def test_batch_profile_caps_use_actual_semantic_input_bytes_and_order_before_scatter(
    monkeypatch, prepared, item_limit, byte_limit
):
    from corpus_structure.semantic.identity import canonical_bytes

    batches, measurements = [], []

    def measure(members):
        values = tuple(member.values for member in members)
        measurements.append(values)
        return len(canonical_bytes(list(values)))

    def batch(members, **_):
        values = tuple(member.values for member in members)
        assert len(values) <= item_limit
        assert len(canonical_bytes(list(values))) <= byte_limit
        batches.append(values)
        if False:
            yield
        return SimpleNamespace(members=tuple((member.member, member.values) for member in members))

    port = SimpleNamespace(
        native_selections=(),
        plan_batch_python=batch,
        batch_max_items=item_limit,
        batch_max_input_bytes=byte_limit,
        batch_input_bytes=measure,
        batch_order_key=lambda member: -member.values,
    )
    executor, observed = execution_case(
        monkeypatch,
        prepared,
        policy_for(prepared, max_claims=4, credits=4),
        ("batch",) * 5,
        {"batch": port},
    )
    result = executor.advance("controlled-demand")
    assert result.receipt_count == 5
    assert batches == [(1, 0), (3, 2), (4,)]
    assert measurements and max(map(len, observed.claim_sets)) <= item_limit
    assert dict(observed.receipts) == {str(i): i for i in range(5)}
    assert len(observed.claims) == 5 and not observed.live and executor.budget.used_bytes == 0


def test_indivisible_semantic_input_capacity_failure_preserves_claimed_siblings(
    monkeypatch, prepared
):
    from corpus_structure.semantic.identity import canonical_bytes

    def content(members):
        return canonical_bytes(["long" if member.values == 0 else "x" for member in members])

    def batch(members, **_):
        assert len(content(members)) <= 5
        if False:
            yield
        return SimpleNamespace(members=tuple((member.member, member.values) for member in members))

    port = SimpleNamespace(
        native_selections=(),
        plan_batch_python=batch,
        batch_max_input_bytes=5,
        batch_input_bytes=lambda members: len(content(members)),
    )
    executor, observed = execution_case(
        monkeypatch,
        prepared,
        policy_for(prepared, max_claims=3, credits=3),
        ("batch",) * 3,
        {"batch": port},
    )
    with pytest.raises(data_operations.NativeDemandExecutionError) as caught:
        executor.advance("controlled-demand")
    assert caught.value.result.receipt_count == 2
    assert len(caught.value.failures) == 1
    assert isinstance(caught.value.failures[0], CapacityExceeded)
    assert dict(observed.receipts) == {"1": 1, "2": 2}
    assert observed.failures[0][0] == "0"
    assert not observed.live and executor.budget.used_bytes == 0


def test_batch_order_failure_settles_every_owned_claim(monkeypatch, prepared):
    def bad_key(_):
        raise ValueError("controlled order failure")

    port = SimpleNamespace(
        native_selections=(), plan_batch_python=lambda *a, **k: None, batch_order_key=bad_key
    )
    executor, observed = execution_case(
        monkeypatch,
        prepared,
        policy_for(prepared, max_claims=3, credits=3),
        ("batch",) * 3,
        {"batch": port},
    )
    with pytest.raises(data_operations.NativeDemandExecutionError) as caught:
        executor.advance("controlled-demand")
    assert caught.value.result.receipt_count == 0
    assert len(caught.value.failures) == 1
    assert "controlled order failure" in str(caught.value.failures[0])
    assert {item for item, _ in observed.failures} == {"0", "1", "2"}
    assert not observed.live and executor.budget.used_bytes == 0


def test_closing_frontier_releases_reserved_work_that_never_started(monkeypatch, prepared):
    from corpus_structure.core.work import ReadyFrontier

    executor, observed = execution_case(
        monkeypatch,
        prepared,
        policy_for(prepared),
        ("scalar",),
        {"scalar": SimpleNamespace(native_selections=())},
    )

    def close_unstarted(plan, _check_active):
        frontier = next(plan)
        assert isinstance(frontier, ReadyFrontier)
        child = frontier.admit()
        assert child is not None
        assert executor.budget.used_bytes == executor.reservation
        assert not executor._physical.requests  # No request or native claim ran.
        assert executor._physical.has_live_requests()
        child.close()
        plan.close()
        assert not executor._physical.has_live_requests()
        assert executor.budget.used_bytes == 0

    monkeypatch.setattr(data_operations, "drive_prepared_work", close_unstarted)
    result = executor.advance("controlled-demand")
    assert result.receipt_count == 0
    assert not observed.claims and not observed.live and executor.budget.used_bytes == 0


def test_reservation_formula_has_one_literal_contract(prepared):
    from dataclasses import replace

    from orchestrate.executor_support import executor_case

    policy = replace(
        policy_for(prepared), max_packet_bytes=65536, max_reply_bytes=4096, max_owned_bytes=143360
    )
    executor = executor_case(prepared=prepared, policy=policy)
    assert policy.max_packet_bytes == 65536 and policy.max_reply_bytes == 4096
    assert executor.reservation == 143360
    with pytest.raises(ValueError, match="exceed owned capacity"):
        executor_case(prepared=prepared, policy=replace(policy, max_owned_bytes=143359))


@pytest.mark.parametrize("form", ["scalar", "batch"])
@pytest.mark.parametrize("mode", ["draft", "native-intent", "uncertain"])
def test_recovery_precedes_fresh_port_and_hydration(monkeypatch, prepared, form, mode):
    from corpus_structure.semantic.claim_lifetime import ClaimSettlementUncertain

    def forbidden(*args, **kwargs):
        raise AssertionError("recovery entered fresh computation")

    executor, observed = execution_case(
        monkeypatch,
        prepared,
        policy_for(prepared),
        (form,) * (2 if form == "batch" else 1),
        {},
    )
    executor._has_draft_path = lambda _: True
    executor.native_io.calls.replies["register_data_execution_origin"] = {
        "origin_id": "origin:controlled",
        "candidates": [],
    }
    executor.native_io.hydrate_inputs = executor._port = forbidden
    recovered = []

    def recover(ready, claim, owner):
        assert claim.request_id in owner.active
        assert executor.budget.used_bytes == 0
        if mode == "native-intent":
            forbidden()
        if mode == "uncertain":
            error = ClaimSettlementUncertain(claim, claim.holder, "exact-intent")
            owner.uncertain[claim.request_id] = error
            raise error
        recovered.append((ready.obligation, "draft"))
        return "intent:" + claim.request_id

    def publish(claim, intent, owner):
        owner.active.pop(claim.request_id)
        observed.live.remove(claim.request_id)
        executor._receipt_count += 1
        return intent.encode()

    def reconcile(claim, intent, owner):
        recovered.append((claim.request_id, "native-intent"))
        return publish(claim, intent, owner)

    executor._recover_answer, executor._publish, executor._reconcile = recover, publish, reconcile
    if mode == "native-intent":
        native_claim = executor.native_io.calls.replies["claim_data_requests"]

        def race(payload):
            result = native_claim(payload)
            for item in result["items"]:
                item["result"].update(action="reconcile", retained_intent_id="intent:native")
            return result

        executor.native_io.calls.replies["claim_data_requests"] = race
    if mode == "uncertain":
        with pytest.raises(data_operations.NativeDemandExecutionError) as caught:
            executor.advance("controlled-demand")
        assert all(isinstance(error, ClaimSettlementUncertain) for error in caught.value.failures)
        assert not recovered and observed.live
    else:
        count = 2 if form == "batch" else 1
        assert executor.advance("controlled-demand").receipt_count == count
        assert recovered == [(str(index), mode) for index in range(count)]
        assert not observed.live
    assert executor.budget.used_bytes == 0


def test_mixed_batch_checks_deferred_draft_before_rehydrating(monkeypatch, prepared):
    from corpus_structure.semantic.data_operation_consumers import HydratedConsumerSelection

    hydrated, computed = [], []

    def batch(members, **_):
        computed.extend(member.values for member in members)
        if False:
            yield
        return SimpleNamespace(members=tuple((member.member, member.values) for member in members))

    executor, observed = execution_case(
        monkeypatch,
        prepared,
        policy_for(prepared, max_claims=4),
        ("batch",) * 4,
        {"batch": SimpleNamespace(native_selections=(), plan_batch_python=batch)},
    )
    executor._has_draft_path = lambda _: True
    executor.native_io.calls.replies["register_data_execution_origin"] = {
        "origin_id": "origin:controlled",
        "candidates": [],
    }

    def hydrate(model, selected, **options):
        identifier = selected.subject
        assert identifier not in {"0", "3"}
        assert identifier not in hydrated, "deferred eligible draft was rehydrated"
        hydrated.append(identifier)
        return HydratedConsumerSelection(
            selected, (), measured_bytes=executor.policy.max_packet_bytes // 2 + 1
        )

    publish_fresh_or_draft = executor._publish

    def publish(claim, intent, owner):
        if not intent.startswith("draft:"):
            return publish_fresh_or_draft(claim, intent, owner)
        owner.active.pop(claim.request_id)
        observed.live.remove(claim.request_id)
        executor._receipt_count += 1
        return intent.encode()

    def recover(ready, claim, owner):
        identifier = ready.obligation
        if identifier in {"0", "3"} or (identifier == "2" and computed):
            return "draft:" + identifier
        return None

    executor.native_io.hydrate_inputs = hydrate
    executor._publish, executor._recover_answer = publish, recover
    assert executor.advance("controlled-demand").receipt_count == 4
    assert hydrated == ["1", "2"]
    assert computed == [1]
    assert len(observed.claims) == 4 and not observed.live


def test_cancelling_submitted_held_claim_waits_for_physical_retirement(monkeypatch, prepared):
    started, release = Event(), Event()

    def run(value, *, execution_owner, **_):
        def compute():
            started.set()
            assert release.wait(5)
            return value

        (answer,) = yield (
            data_operations.PreparedWork(lambda: execution_owner.submit_python(compute)),
        )
        return answer

    executor, observed = execution_case(
        monkeypatch,
        prepared,
        policy_for(prepared),
        ("scalar",),
        {"scalar": SimpleNamespace(native_selections=(), plan_python=run)},
    )
    executor._has_draft_path = lambda _: True
    executor.native_io.calls.replies["register_data_execution_origin"] = {
        "origin_id": "origin:controlled",
        "candidates": [],
    }

    def cancel_after_submission(plan, _owner):
        frontier = next(plan)
        child = frontier.admit()
        assert child is not None
        (work,) = next(child)
        handle = work.try_submit()
        assert handle is not None and started.wait(5)
        try:
            handle.cancel()
            child.close()
            plan.close()
            assert not observed.failures and observed.live == {"0"}
        finally:
            release.set()

    monkeypatch.setattr(data_operations, "drive_prepared_work", cancel_after_submission)
    with pytest.raises(data_operations.NativeDemandExecutionError):
        executor.advance("controlled-demand")
    assert observed.failures[0][0] == "0"
    assert not observed.live and executor.budget.used_bytes == 0
