"""Physical retirement determines byte-credit release, including nested failures."""

from concurrent.futures import Future
from types import SimpleNamespace
from typing import cast

import pytest

from corpus_structure.core.work import PhysicalRetirementUncertain
from corpus_structure.methods.native_host import NativeHostResidency, NativeRetirementUncertain
from corpus_structure.orchestrate.data_operations import _PythonWork, _RunExecution
from corpus_structure.semantic.cpu_execution import CPUExecutionScope, OwnedByteBudget


@pytest.mark.parametrize("batch", [False, True])
def test_managed_stop_drains_running_transport_before_releasing_its_exact_claim(batch):
    from threading import Event, RLock

    from corpus_structure.core.execution_control import (
        ExecutionStopped,
        ExecutionStopRequest,
        execution_stop_scope,
    )
    from corpus_structure.core.execution_policy import CharacterizationExecutionPolicy
    from corpus_structure.orchestrate.data_operations import (
        _check_batch_active,
        _check_claim_active,
        _RequestExecution,
    )
    from corpus_structure.orchestrate.execution_host import ProcessExecutionHost

    request = ExecutionStopRequest()
    running, retired = Event(), Event()
    claim = SimpleNamespace(task_id=7, attempt=3, holder="actual-owner")
    key = (claim.task_id, claim.attempt, claim.holder)
    owner = SimpleNamespace(lock=RLock(), active={key: claim}, uncertain={}, lost={})

    # The batch activity API also checks the shared lease owner itself.
    class BatchOwner:
        def __call__(self):
            pass

        def check_claim(self, candidate):
            assert owner.active[key] is candidate

    activity = BatchOwner()
    released = []

    def release(candidate, actual_owner, error, *, phase):
        assert candidate is claim and actual_owner is owner
        assert retired.is_set() and work.future.done()
        released.append(key)
        del owner.active[key]

    executor = SimpleNamespace(
        prepared=SimpleNamespace(release_id="test:transport-stop"),
        policy=CharacterizationExecutionPolicy(workers=1, max_submissions=1),
        port_workers=1,
        nemotron_endpoint=None,
        analytics_settings=None,
        engine=None,
        fitter_engine=None,
        _contexts={},
        _claim_owner=owner,
        _known_failure=release,
        _member_failures=[],
    )

    def compute():
        running.set()
        try:
            while True:
                if batch:
                    _check_batch_active(activity, (claim,))
                else:
                    _check_claim_active(activity, claim)
                request.requested.wait(0.01)
        finally:
            retired.set()

    host = ProcessExecutionHost()
    try:
        with execution_stop_scope(request), host.run(executor.policy) as token:
            with host.execution(executor, token) as physical:
                lease = host.budget.admit(32)
                transport = _RequestExecution(physical, lease)
                work = transport.submit_python(compute)
                lease.release()
                assert running.wait(2)
                request.requested.set()
            assert physical.physical_retired
            assert released == [key] and not owner.active
            assert host.budget.used_bytes == 0
            assert isinstance(work.future.exception(), ExecutionStopped)
    finally:
        request.requested.set()
        host.close()


@pytest.mark.parametrize("native", [False, True])
def test_nlp_drain_cannot_release_an_unproven_pdf_borrower(native):
    budget = OwnedByteBudget(100)
    reservation = budget.admit(100)
    future = Future()
    failure = (NativeRetirementUncertain if native else PhysicalRetirementUncertain)("still owned")
    future.set_exception(
        ExceptionGroup("calculation and teardown", [ValueError("calculation"), failure])
    )
    work = _PythonWork(future, reservation.release)
    assert not work.retire()
    assert budget.used_bytes == 100
    work.drained = True  # Proven NLP host-group death only.
    assert work.retire() is native
    assert budget.used_bytes == (0 if native else 100)
    if native:
        assert work.retire() and budget.used_bytes == 0


def test_provider_residents_follow_frozen_demand_not_all_available_factories(monkeypatch, tmp_path):
    from corpus_structure.methods.native_profiles import NativeProfile, NativeSelection
    from corpus_structure.methods.pm2_worker import preflight_pm2_residents

    acquired = []
    declared = []
    preflight_calls = []
    selection = NativeSelection(
        NativeProfile(
            "spacy", {"distributions_sha256": "selected"}, {"files": {}}, {}, "float32", "cupy"
        ),
        tmp_path,
    )

    def preflight(**request):
        preflight_calls.append(request["providers"])
        return {"distributions_sha256": "selected"}

    monkeypatch.setattr(f"{preflight_pm2_residents.__module__}.preflight_pm2_residents", preflight)

    def acquire(operation, _context=None):
        if operation != "selected-provider":
            raise AssertionError("unrequested model assets were acquired")
        acquired.append(operation)
        return SimpleNamespace(native_selections=(selection,))

    scope = _RunExecution.__new__(_RunExecution)
    scope.executor = SimpleNamespace(
        capability_factories={"selected-provider": object(), "unrequested-provider": object()},
        _port=acquire,
        model=SimpleNamespace(
            operation=lambda _: SimpleNamespace(capabilities=SimpleNamespace(prepared_factory=None))
        ),
        policy=SimpleNamespace(max_owned_bytes=100),
        reservation=1,
    )
    scope.executor._target_context = SimpleNamespace(
        model=scope.executor.model, cpu=None, prepared_schema=False
    )
    scope.host = SimpleNamespace(ensure_request_room=lambda _: None)
    scope.cpu = cast(CPUExecutionScope, SimpleNamespace(prepare=lambda: None, preparation_bytes=0))
    scope.native_hosts = cast(
        NativeHostResidency, SimpleNamespace(declare=lambda values: declared.append(tuple(values)))
    )
    scope._selected_operations = None
    scope._target_ports = None
    scope._prepared_residents = set()
    scope.select_operations(("pure-cpu", "selected-provider"))
    scope.select_operations(("selected-provider", "pure-cpu"))
    assert acquired == ["selected-provider"] and declared == [(selection,)]
    assert preflight_calls == [("spacy",)]
    with pytest.raises(ValueError, match="frozen operation closure"):
        scope.select_operations(("unrequested-provider",))
