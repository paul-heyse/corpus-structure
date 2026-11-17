"""Request admission shares actual retained CPU preparation and physical leases."""

import importlib
import inspect
import json
from concurrent.futures import Future
from contextlib import nullcontext
from threading import Event
from types import SimpleNamespace
from typing import Any, cast

import pytest

from corpus_structure.core.execution_policy import CharacterizationExecutionPolicy
from corpus_structure.orchestrate import data_operations
from corpus_structure.orchestrate.data_operations import (
    NativeDemandExecutor,
    _InvocationExecution,
    _OwnedPythonPool,
)
from corpus_structure.semantic import SourceArtifact, SourceBundle, prepare_release
from corpus_structure.semantic.cpu_execution import (
    CapacityExceeded,
    OwnedByteBudget,
    release_capsule,
)
from corpus_structure.semantic.data_operation_cpu import PythonCPUDescriptor, plan_cpu_call


@pytest.fixture(scope="module")
def prepared():
    return prepare_release(
        SourceBundle(
            "admission",
            (
                SourceArtifact(
                    "admission",
                    b"""id: urn:admission
name: admission
prefixes: {a: 'urn:admission:'}
default_prefix: a
types:
  string: {base: str, uri: 'http://www.w3.org/2001/XMLSchema#string'}
classes:
  Thing:
    attributes:
      id: {range: string, required: true}
""",
                ),
            ),
        )
    )


def policy_for(prepared, *, max_claims=2, credits=2):
    packet = max(65536, len(release_capsule(prepared)))
    reply = 4096
    reservation = 2 * packet + 3 * reply
    return CharacterizationExecutionPolicy(
        workers=2,
        max_submissions=2,
        max_claims=max_claims,
        max_packet_bytes=packet,
        max_reply_bytes=reply,
        max_native_request_bytes=1,
        max_native_reply_bytes=1,
        max_owned_bytes=credits * reservation,
    )


def controlled_executor(monkeypatch, prepared, policy, requests, ports):
    """Replace native I/O only; exercise production admission and physical owners."""
    executor = cast(Any, NativeDemandExecutor.__new__(NativeDemandExecutor))
    executor.prepared, executor.policy = prepared, policy
    executor.engine = SimpleNamespace(begin=lambda: nullcontext(None))
    executor.fitter_engine = None
    executor.nemotron_endpoint = None
    executor.port_workers = 2
    executor.reservation = 2 * policy.max_packet_bytes + 3 * policy.max_reply_bytes
    executor.budget = OwnedByteBudget(policy.max_owned_bytes)
    executor._preparation_bytes = 0
    executor._failed_requests = set()
    executor._quarantined = False
    executor.capability_factories = dict.fromkeys(ports, object())
    executor.model = SimpleNamespace(
        operation=lambda operation: SimpleNamespace(
            capabilities=SimpleNamespace(
                forms=("batch",) if operation == "batch" else ("scalar",),
                prepared_factory=None,
            ),
            external=None,
        )
    )
    context = SimpleNamespace(
        basis=SimpleNamespace(prepared=prepared, key=(prepared.release_id, "runtime:controlled")),
        model=executor.model,
        cpu=None,
        prepared_schema=False,
    )
    executor._target_context = context
    executor._contexts = {context.basis.key: context}
    executor._execution_context = lambda _: context
    executor._ready_context = lambda _: context
    executor._prepare_ready = lambda item, _: item
    executor._port = lambda operation, _context=None: ports[operation]
    ready = tuple(
        SimpleNamespace(
            operation=operation,
            obligation=str(index),
            native=json.dumps({"request_id": str(index), "generation": 1}).encode(),
            binding_result=None,
        )
        for index, operation in enumerate(requests)
    )
    monkeypatch.setattr(
        data_operations,
        "DemandPlanner",
        lambda *_: SimpleNamespace(ready=lambda *_args, **_kw: ready, fulfilled_request_ids=()),
    )
    monkeypatch.setattr(data_operations, "DataOperationStorage", lambda _: None)
    observed = SimpleNamespace(claims=[], receipts=[], failures=[], live=set(), windows=[])

    def claim(item, owner, *, physical=None):
        index = item.obligation
        observed.claims.append((index, executor.budget.used_bytes))
        observed.live.add(index)
        observed.windows.append(len(observed.live))
        if physical is not None:
            physical.hydrated_inputs = executor._hydrate(item, physical)
        return SimpleNamespace(
            request_id=index,
            generation=1,
            attempt=1,
            fence=dict(
                request_id=index,
                generation=1,
                task_id=int(index) + 1,
                attempt=1,
                holder="controlled",
            ),
        ), {
            "state": "claimed",
            "action": "execute",
        }

    def publish(claim, answer, owner):
        observed.receipts.append((claim.request_id, answer))
        observed.live.remove(claim.request_id)
        return claim.request_id.encode()

    def failed(claim, owner, error, *, phase):
        observed.failures.append((claim.request_id, error))
        observed.live.remove(claim.request_id)

    executor._claim = claim
    def hydrate(item, physical, **_kwargs):
        physical.hydrated_sizes[item.obligation] = len(item.obligation)
        return int(item.obligation)

    executor._hydrate = hydrate
    executor._retain_answer = lambda _item, _claim, answer, *_args, **_kw: answer
    executor._publish = publish
    executor._known_failure = failed
    return executor, observed


class Active:
    def __call__(self):
        pass

    def check_claim(self, _):
        pass


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

    def plan(value, *, check_active, execution_owner, **_):
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
    executor, observed = controlled_executor(
        monkeypatch, prepared, policy, ("prepared",) * 3, {"prepared": port}
    )
    capsule_size = len(release_capsule(prepared))
    assert 0 < capsule_size < executor.reservation
    assert policy.max_owned_bytes == 2 * executor.reservation and policy.max_claims == 2
    with _OwnedPythonPool(2) as pool, _InvocationExecution(executor, pool) as physical:
        executor._physical = physical
        physical.select_operations(("prepared",))
        assert executor.budget.used_bytes == capsule_size
        assert executor.policy.max_claims == 2
        receipts, _, _, failures = executor._drive_sweep(({},), b"{}", Active())
        assert executor.budget.used_bytes == capsule_size
        assert len(receipts) == 3 - fail_first and len(failures) == fail_first
    assert [index for index, _ in observed.claims] == ["0", "1", "2"]
    assert all(
        capsule_size + executor.reservation <= used <= policy.max_owned_bytes
        for _, used in observed.claims
    )
    assert max(observed.windows) <= policy.max_claims
    assert observed.receipts == (
        [("1", 8), ("2", 9)] if fail_first else [("0", 7), ("1", 8), ("2", 9)]
    )
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
    executor, observed = controlled_executor(
        monkeypatch,
        prepared,
        policy_for(prepared, credits=4),
        ("batch",) * 5 + ("scalar",),
        ports,
    )
    with _OwnedPythonPool(2) as pool, _InvocationExecution(executor, pool) as physical:
        executor._physical = physical
        physical.select_operations(ports)
        receipts, _, _, failures = executor._drive_sweep(({},), b"{}", Active())
    assert len(receipts) == 6 and not failures, (receipts, failures)
    assert sum(batches) == 5 and max(batches) <= 2 and len(batches) >= 3
    assert max(observed.windows) <= 2
    assert all(used <= executor.policy.max_owned_bytes for _, used in observed.claims)
    assert executor.budget.used_bytes == 0


def test_preparation_that_cannot_hold_one_request_refuses_before_claim(monkeypatch, prepared):
    policy = policy_for(prepared, credits=1)
    port = SimpleNamespace(native_selections=(), requires_prepared_schema=True)
    executor, observed = controlled_executor(
        monkeypatch, prepared, policy, ("prepared",), {"prepared": port}
    )
    with _OwnedPythonPool(2) as pool, _InvocationExecution(executor, pool) as physical:
        executor._physical = physical
        with pytest.raises(CapacityExceeded, match="preparation and one complete request"):
            physical.select_operations(("prepared",))
    assert not observed.claims and executor.budget.used_bytes == 0


def test_reduced_credit_allows_progress_while_an_old_physical_share_retires(
    monkeypatch, prepared
):
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

    executor, observed = controlled_executor(
        monkeypatch,
        prepared,
        policy_for(prepared),
        ("scalar",) * 3,
        {"scalar": SimpleNamespace(native_selections=(), plan_python=plan)},
    )
    with _OwnedPythonPool(2) as pool, _InvocationExecution(executor, pool) as physical:
        executor._physical = physical
        physical.select_operations(("scalar",))
        receipts, _, _, failures = executor._drive_sweep(({},), b"{}", Active())
    assert len(receipts) == 3 and not failures and third_started.is_set()
    assert [index for index, _ in observed.claims] == ["0", "1", "2"]
    assert executor.budget.used_bytes == 0


def test_cancel_before_admitted_plan_starts_releases_its_credit(monkeypatch, prepared):
    executor, observed = controlled_executor(
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
    executor._drive_sweep(({},), b"{}", Active())
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

    class Body:
        def __init__(self, identifier):
            self.identifier = identifier

    def batch(members, *, execution_owner, **_):
        identifiers = tuple(member.values.identifier for member in members)
        batches.append(identifiers)
        if identifiers == ("0",):
            # The overflowing member's decoded bodies have been discarded before
            # stage B and the current physical call; only its native claim stays.
            assert references["1"][0]() is None
            assert "1" not in execution_owner.consumer_inputs
        if False:
            yield
        return SimpleNamespace(members=tuple((member.member, member.values.identifier) for member in members))

    executor, observed = controlled_executor(
        monkeypatch, prepared, policy_for(prepared, max_claims=3, credits=2),
        ("batch",) * 3, {"batch": SimpleNamespace(native_selections=(), plan_batch_python=batch)},
    )

    def hydrate(item, physical, **_):
        hydrations.append(item.obligation)
        body = Body(item.obligation)
        references.setdefault(item.obligation, []).append(weakref.ref(body))
        physical.hydrated_sizes[item.obligation] = executor.policy.max_packet_bytes // 2 + 1
        physical.consumer_inputs[item.obligation] = body
        physical.consumer_results[item.obligation] = body
        physical.binding_rows[item.obligation] = body
        return body

    executor._hydrate = hydrate
    with _OwnedPythonPool(2) as pool, _InvocationExecution(executor, pool) as physical:
        executor._physical = physical
        physical.select_operations(("batch",))
        receipts, _, _, failures = executor._drive_sweep(({},), b"{}", Active())
    assert not failures and len(receipts) == 3
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

    executor, observed = controlled_executor(
        monkeypatch, prepared, policy_for(prepared), ("scalar",) * 6,
        {"scalar": SimpleNamespace(native_selections=(), plan_python=scalar)},
    )

    def page(index, _authorization):
        prepared_pages.append(index)
        return [
            SimpleNamespace(
                operation="scalar", obligation=str(identifier), binding_result=None,
                native=json.dumps({"request_id": str(identifier), "generation": 1}).encode(),
            )
            for identifier in range(2 * index, 2 * index + 2)
        ], (), (), ()

    executor._prepare_page = page
    driver = data_operations.drive_prepared_work

    def drive(plan, owner):
        driver_calls.append(1)
        return driver(plan, owner)

    monkeypatch.setattr(data_operations, "drive_prepared_work", drive)
    with _OwnedPythonPool(2) as pool, _InvocationExecution(executor, pool) as physical:
        executor._physical = physical
        physical.select_operations(("scalar",))
        receipts, _, _, failures = executor._drive_sweep(range(3), b"{}", Active())
    assert prepared_pages == [0, 1, 2] and driver_calls == [1]
    assert len(receipts) == 6 and not failures
    assert max(observed.windows) <= 2 and executor.budget.used_bytes == 0
