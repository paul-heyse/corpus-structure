"""Native CPU lifetime failures through the normal invocation close owner."""

import os
import signal
import threading
import time
from concurrent.futures.process import BrokenProcessPool
from typing import Any, cast

import pytest

from corpus_structure.core.execution_policy import CharacterizationExecutionPolicy
from corpus_structure.semantic import cpu_execution
from corpus_structure.semantic.cpu_execution import CPUExecutionScope, CPURequestCancelled
from semantic.test_cpu_execution import packet
from semantic.test_formal_evidence import prepared as prepared


# One second permits real spawned-worker scheduling while bounding failure cleanup.
_CLOSE_GRACE = 1.0
_EXIT_GRACE = 1.0
_SCHEDULING_SLACK = 2.0


def _short_graces(monkeypatch):
    monkeypatch.setattr(cpu_execution, "_COOPERATIVE_CLOSE_SECONDS", _CLOSE_GRACE)
    monkeypatch.setattr(cpu_execution, "_WORKER_EXIT_SECONDS", _EXIT_GRACE)


def _close_bound():
    return (cpu_execution._COOPERATIVE_CLOSE_SECONDS
            + cpu_execution._WORKER_EXIT_SECONDS + _SCHEDULING_SLACK)


def _executor_with_event(monkeypatch, event):
    native_executor = cpu_execution.ProcessPoolExecutor

    def executor(**kwargs):
        kwargs.update(initializer=_initialize_with_event,
                      initargs=(kwargs["initializer"], kwargs["initargs"], event))
        return native_executor(**kwargs)

    monkeypatch.setattr(cpu_execution, "ProcessPoolExecutor", executor)


def test_cpu_close_policy_graces_are_five_seconds():
    assert (cpu_execution._COOPERATIVE_CLOSE_SECONDS,
            cpu_execution._WORKER_EXIT_SECONDS) == (5.0, 5.0)


def _blocked_initializer(started):
    signal.signal(signal.SIGTERM, signal.SIG_IGN)
    started.set()
    while True:
        time.sleep(1)


def _ignore_stop_and_term(started):
    signal.signal(signal.SIGTERM, signal.SIG_IGN)
    started.set()
    while True:
        time.sleep(1)


def _fail_worker():
    os._exit(23)


def _cooperative_worker(started):
    started.set()
    while True:
        cpu_execution._worker_active()
        time.sleep(0.01)


def _ownership(execution):
    return cpu_execution._PoolOwnership.capture(execution._executor())


def _assert_retired(execution, ownership):
    assert not any(process.is_alive() for process in ownership.processes)
    assert ownership.manager is None or not ownership.manager.is_alive()
    assert execution.budget.used_bytes == 0
    assert not execution._admissions
    execution.close()
    execution.abort()
    with pytest.raises(RuntimeError, match="closed"):
        execution.try_admit()


def test_close_kills_noncooperative_initializer_after_cooperative_grace(prepared, monkeypatch):
    _short_graces(monkeypatch)
    execution = CPUExecutionScope(prepared, CharacterizationExecutionPolicy(workers=1))
    started = execution._context.Event()
    native_executor = cpu_execution.ProcessPoolExecutor

    def executor(**kwargs):
        kwargs.update(initializer=_blocked_initializer, initargs=(started,))
        return native_executor(**kwargs)

    monkeypatch.setattr(cpu_execution, "ProcessPoolExecutor", executor)
    ownership = None
    try:
        permit = execution.try_admit()
        handle = execution.submit(permit, packet(prepared), {})
        assert started.wait(30), "worker did not enter blocked initializer"
        ownership = _ownership(execution)
        before = time.monotonic()
        execution.close()
        elapsed = time.monotonic() - before
        assert cpu_execution._COOPERATIVE_CLOSE_SECONDS - 0.1 <= elapsed < _close_bound()
        with pytest.raises(CPURequestCancelled):
            handle.collect()
    finally:
        execution.close()
    assert ownership is not None
    _assert_retired(execution, ownership)


def test_close_cooperatively_drains_running_work_without_whole_pool_abort(prepared, monkeypatch):
    _short_graces(monkeypatch)
    execution = CPUExecutionScope(prepared, CharacterizationExecutionPolicy(workers=1))
    started = execution._context.Event()
    # Synchronization objects cross spawn through the public factory seam.
    _executor_with_event(monkeypatch, started)
    pool = execution._executor()
    submit = pool.submit
    # The child gets its event from the initializer, not a pickled task argument.
    monkeypatch.setattr(pool, "submit", lambda *_args: submit(_cooperative_from_initializer))
    ownership = None
    checks = []

    def active():
        checks.append(execution._closed)

    try:
        permit = execution.try_admit()
        handle = execution.submit(permit, packet(prepared), {}, active)
        assert started.wait(30)
        ownership = _ownership(execution)
        before = time.monotonic()
        execution.close()
        assert time.monotonic() - before < cpu_execution._COOPERATIVE_CLOSE_SECONDS
        assert handle.future.done()
        assert checks == [False], "discarding close invoked the caller's activity callback"
    finally:
        execution.close()
    assert ownership is not None
    _assert_retired(execution, ownership)


_TEST_EVENT: Any = None


def _initialize_with_event(initializer, args, event):
    global _TEST_EVENT
    _TEST_EVENT = event
    initializer(*args)


def _cooperative_from_initializer():
    return _cooperative_worker(_TEST_EVENT)


def _ignore_from_initializer():
    return _ignore_stop_and_term(_TEST_EVENT)


def test_close_reaps_term_ignoring_sibling_of_broken_worker(prepared, monkeypatch):
    _short_graces(monkeypatch)
    execution = CPUExecutionScope(
        prepared, CharacterizationExecutionPolicy(workers=2, max_submissions=2)
    )
    started = execution._context.Event()
    _executor_with_event(monkeypatch, started)
    pool = execution._executor()
    submit = pool.submit
    jobs = iter((_ignore_from_initializer, _fail_worker))
    monkeypatch.setattr(pool, "submit", lambda *_args: submit(next(jobs)))
    ownership = None
    try:
        first = execution.submit(execution.try_admit(), packet(prepared), {})
        assert started.wait(30)
        second = execution.submit(execution.try_admit(), packet(prepared), {})
        ownership = _ownership(execution)
        deadline = time.monotonic() + 30
        while not any(process.exitcode == 23 for process in ownership.processes):
            assert time.monotonic() < deadline, "second worker did not exit"
            time.sleep(0.01)
        before = time.monotonic()
        execution.close()
        assert time.monotonic() - before < _close_bound()
        assert first.future.done()
        with pytest.raises(BrokenProcessPool):
            second.future.result()
    finally:
        execution.close()
    assert ownership is not None
    _assert_retired(execution, ownership)


def test_close_preserves_primary_failure_and_owned_credit_when_death_unproven(
    prepared, monkeypatch
):
    execution = CPUExecutionScope(prepared)
    execution.try_admit()
    retained = execution.budget.used_bytes
    sentinel = RuntimeError("death could not be confirmed")

    def refuse_shutdown(*_args):
        raise sentinel

    monkeypatch.setattr(cpu_execution._PoolOwnership, "shutdown", refuse_shutdown)
    primary = ValueError("primary operation failure")
    with pytest.raises(ValueError, match="primary operation failure") as failure:
        try:
            raise primary
        finally:
            execution.close()
    assert failure.value is primary
    assert any("CPU cleanup also failed" in note for note in primary.__notes__)
    assert execution.budget.used_bytes == retained
    assert execution._pool is not None
    # An unproven close is a terminal honest failure, not a recovery route.
    with pytest.raises(ExceptionGroup, match="CPU cleanup failed"):
        execution.close()
    assert execution.budget.used_bytes == retained
    # This test never submitted work; release the native executor's queues.
    execution._pool.shutdown()


def test_close_unblocks_third_submission_behind_broken_pool_lock(prepared, monkeypatch):
    _short_graces(monkeypatch)
    execution = CPUExecutionScope(
        prepared, CharacterizationExecutionPolicy(workers=2, max_submissions=3)
    )
    started = execution._context.Event()
    _executor_with_event(monkeypatch, started)
    pool = execution._executor()
    native = cast(Any, pool)
    submit = pool.submit
    third_entered = threading.Event()
    third_finished = threading.Event()
    close_finished = threading.Event()
    submission_errors = []
    close_errors = []
    jobs = iter((_ignore_from_initializer, _fail_worker, _fail_worker))
    calls = 0

    def native_submit(*_args):
        nonlocal calls
        calls += 1
        if calls == 3:
            third_entered.set()
        return submit(next(jobs))

    monkeypatch.setattr(pool, "submit", native_submit)
    content = packet(prepared)
    permits = [execution.try_admit() for _ in range(3)]
    ownership = _ownership(execution)

    def submit_third():
        try:
            execution.submit(permits[2], content, {})
        except BaseException as error:
            submission_errors.append(error)
        finally:
            third_finished.set()

    def close():
        try:
            execution.close()
        except BaseException as error:
            close_errors.append(error)
        finally:
            close_finished.set()

    caller = threading.Thread(target=submit_third, daemon=True)
    closer = threading.Thread(target=close, daemon=True)
    try:
        first = execution.submit(permits[0], content, {})
        assert started.wait(30)
        execution.submit(permits[1], content, {})
        deadline = time.monotonic() + 30
        while not any(process.exitcode == 23 for process in ownership.processes):
            assert time.monotonic() < deadline, "second worker did not exit"
            time.sleep(0.01)
        # submit wakes before spawning dynamically. If the manager rebuilds its
        # sentinel list before that spawn finishes, it needs another wakeup to
        # observe the new worker's death. Establish the actual broken-lock state
        # deliberately; the close below still owns all failure handling.
        # The adapter owns the same CPython shutdown lock and manager internals
        # (cpu_execution._PoolOwnership.shutdown); this constructs its failure interleaving.
        native._executor_manager_thread_wakeup.wakeup()
        while not native._broken or not native._shutdown_lock.locked():
            assert time.monotonic() < deadline, "manager did not enter broken-pool cleanup"
            time.sleep(0.01)
        ownership.manager = native._executor_manager_thread
        caller.start()
        assert third_entered.wait(5)
        assert not third_finished.is_set(), "third submission did not block in the native lock"
        retained = execution.budget.used_bytes
        credits_at_kill = []
        for process in ownership.processes:
            kill = process.kill

            def observe_kill(kill=kill):
                credits_at_kill.append(execution.budget.used_bytes)
                kill()

            monkeypatch.setattr(process, "kill", observe_kill)
        before = time.monotonic()
        closer.start()
        assert close_finished.wait(_close_bound()), "normal close waited indefinitely behind native submit"
        assert time.monotonic() - before < _close_bound()
        assert not close_errors
        assert third_finished.wait(1)
        assert len(submission_errors) == 1
        assert isinstance(submission_errors[0], BrokenProcessPool)
        assert retained > 0
        assert credits_at_kill and all(credit == retained for credit in credits_at_kill)
        with pytest.raises(CPURequestCancelled):
            first.collect()
        _assert_retired(execution, ownership)
    finally:
        # A failed watchdog assertion must still contain these deliberately
        # noncooperative children and unblock the native manager/submitter.
        for process in ownership.processes:
            if process.is_alive():
                process.kill()
        deadline = time.monotonic() + 5
        for process in ownership.processes:
            process.join(max(0, deadline - time.monotonic()))
        if caller.ident is not None:
            caller.join(max(0, deadline - time.monotonic()))
        if closer.ident is not None:
            closer.join(max(0, deadline - time.monotonic()))
        execution.close()


def _die_holding_cancellation_lock():
    cpu_execution._WORKER_CANCELLATION.get_lock().acquire()
    _TEST_EVENT.set()
    os._exit(24)


def _die_holding_stop_lock():
    cpu_execution._WORKER_STOP._cond.acquire()
    _TEST_EVENT.set()
    os._exit(24)


@pytest.mark.parametrize("abandoned", ["cancellation", "stop"])
def test_close_bounds_abandoned_ipc_lock(prepared, monkeypatch, abandoned):
    _short_graces(monkeypatch)
    execution = CPUExecutionScope(prepared, CharacterizationExecutionPolicy(workers=1))
    started = execution._context.Event()
    _executor_with_event(monkeypatch, started)
    pool = execution._executor()
    submit = pool.submit
    job = _die_holding_cancellation_lock if abandoned == "cancellation" else _die_holding_stop_lock
    monkeypatch.setattr(pool, "submit", lambda *_args: submit(job))
    content = packet(prepared)
    ownership = None
    try:
        handle = execution.submit(execution.try_admit(), content, {})
        assert started.wait(30)
        ownership = _ownership(execution)
        deadline = time.monotonic() + 30
        while not any(process.exitcode == 24 for process in ownership.processes):
            assert time.monotonic() < deadline, "worker did not abandon its IPC lock"
            time.sleep(0.01)
        retained = execution.budget.used_bytes
        cancelled = threading.Event()

        def cancel():
            handle.cancel()
            cancelled.set()

        caller = threading.Thread(target=cancel, daemon=True)
        caller.start()
        assert cancelled.wait(1), "logical cancellation waited on an abandoned IPC lock"
        caller.join()
        before = time.monotonic()
        with pytest.raises(CPURequestCancelled):
            handle.collect()
        assert time.monotonic() - before < 1
        # Parent admission must not read the worker's stop Event or block on
        # a dead child's cancellation lock. Failed admission restores its bytes.
        retained = execution.budget.used_bytes
        before = time.monotonic()
        if abandoned == "cancellation":
            with pytest.raises(RuntimeError, match="cancellation state"):
                execution.try_admit()
            assert execution.budget.used_bytes == retained
        else:
            permit = execution.try_admit()
            execution.release_admission(permit)
        assert time.monotonic() - before < 1
        before = time.monotonic()
        if abandoned == "cancellation":
            execution.close()
            assert time.monotonic() - before < cpu_execution._COOPERATIVE_CLOSE_SECONDS
            _assert_retired(execution, ownership)
        else:
            with pytest.raises(ExceptionGroup, match="CPU cleanup failed") as failure:
                execution.close()
            assert (cpu_execution._COOPERATIVE_CLOSE_SECONDS
                    + cpu_execution._WORKER_EXIT_SECONDS - 0.1
                    <= time.monotonic() - before < _close_bound())
            inner = failure.value.exceptions[0]
            assert isinstance(inner, ExceptionGroup)
            assert "physical retirement" in str(inner.exceptions[0])
            assert "cpu-pool-stop" in str(inner.exceptions[0])
            assert handle._cancelled and execution._closed
            assert not execution._physical_retired
            assert execution.budget.used_bytes == retained
            assert not any(process.is_alive() for process in ownership.processes)
            assert ownership.manager is None or not ownership.manager.is_alive()
            # Do not claim a blocked cooperative signal helper has retired.
            with pytest.raises(ExceptionGroup, match="CPU cleanup failed"):
                execution.close()
            assert execution.budget.used_bytes == retained
    finally:
        if ownership is not None:
            for process in ownership.processes:
                if process.is_alive():
                    process.kill()
            for process in ownership.processes:
                process.join(timeout=5)
        if not execution._close_finished:
            execution.close()
