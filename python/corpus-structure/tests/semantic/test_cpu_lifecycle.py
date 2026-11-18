"""Native CPU lifetime failures through the normal invocation close owner."""

import multiprocessing
import os
import signal
import threading
import time
from concurrent.futures.process import BrokenProcessPool
from contextlib import suppress
from typing import Any, cast

import pytest

from corpus_structure.core.execution_policy import CharacterizationExecutionPolicy
from corpus_structure.semantic import cpu_execution
from corpus_structure.semantic.cpu_execution import CPUExecutionScope, CPURequestCancelled
from semantic.cpu_execution_support import packet
from semantic.cpu_execution_support import prepared as prepared

# One second permits real spawned-worker scheduling while bounding failure cleanup.
_CLOSE_GRACE = 1.0
_EXIT_GRACE = 1.0
_SCHEDULING_SLACK = 2.0


def _short_graces(monkeypatch):
    monkeypatch.setattr(cpu_execution, "_COOPERATIVE_CLOSE_SECONDS", _CLOSE_GRACE)
    monkeypatch.setattr(cpu_execution, "_WORKER_EXIT_SECONDS", _EXIT_GRACE)


def _close_bound():
    return (
        cpu_execution._COOPERATIVE_CLOSE_SECONDS
        + cpu_execution._WORKER_EXIT_SECONDS
        + _SCHEDULING_SLACK
    )


def _executor_with_event(monkeypatch, event):
    native_executor = cpu_execution.ProcessPoolExecutor

    def executor(**kwargs):
        kwargs.update(
            initializer=_initialize_with_event,
            initargs=(kwargs["initializer"], kwargs["initargs"], event),
        )
        return native_executor(**kwargs)

    monkeypatch.setattr(cpu_execution, "ProcessPoolExecutor", executor)


def test_cpu_close_policy_graces_are_five_seconds():
    assert (cpu_execution._COOPERATIVE_CLOSE_SECONDS, cpu_execution._WORKER_EXIT_SECONDS) == (
        5.0,
        5.0,
    )


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
        handle = execution.submit_formal(permit, packet(prepared))
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
        handle = execution.submit_formal(permit, packet(prepared), active)
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
        first = execution.submit_formal(execution.try_admit(), packet(prepared))
        assert started.wait(30)
        second = execution.submit_formal(execution.try_admit(), packet(prepared))
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
            execution.submit_formal(permits[2], content)
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
        first = execution.submit_formal(permits[0], content)
        assert started.wait(30)
        execution.submit_formal(permits[1], content)
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
        assert close_finished.wait(_close_bound()), (
            "normal close waited indefinitely behind native submit"
        )
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
        handle = execution.submit_formal(execution.try_admit(), content)
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
            assert (
                cpu_execution._COOPERATIVE_CLOSE_SECONDS + cpu_execution._WORKER_EXIT_SECONDS - 0.1
                <= time.monotonic() - before
                < _close_bound()
            )
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


_TERMINAL_GATE: Any = None
_TERMINAL_READY: Any = None


def _initialize_terminal_worker(initializer, args, gate, ready, active):
    global _TERMINAL_GATE, _TERMINAL_READY, _TEST_EVENT
    initializer(*args)
    _TERMINAL_GATE, _TERMINAL_READY, _TEST_EVENT = gate, ready, active


def _terminal_worker_ready():
    state = {
        "pid": os.getpid(),
        "group": os.getpgrp(),
        "ignores_sigint": signal.getsignal(signal.SIGINT) == signal.SIG_IGN,
    }
    _TERMINAL_READY.put(state)
    if not _TERMINAL_GATE.wait(30):
        raise TimeoutError("terminal control did not release worker preparation")
    return state["pid"]


def _terminal_group_coordinator(channel, capsule, content):
    """Real isolated process group; no signal is sent to the pytest/operator group."""
    os.setsid()
    execution = None
    ready = None
    try:
        cpu_execution._COOPERATIVE_CLOSE_SECONDS = _CLOSE_GRACE
        cpu_execution._WORKER_EXIT_SECONDS = _EXIT_GRACE
        context = multiprocessing.get_context("spawn")
        gate, active, ready = context.Event(), context.Event(), context.Queue()
        native_executor = cpu_execution.ProcessPoolExecutor

        def executor(**kwargs):
            kwargs.update(
                initializer=_initialize_terminal_worker,
                initargs=(kwargs["initializer"], kwargs["initargs"], gate, ready, active),
            )
            return native_executor(**kwargs)

        cast(Any, cpu_execution).ProcessPoolExecutor = executor
        execution = CPUExecutionScope(
            cpu_execution.hydrate_capsule(capsule),
            CharacterizationExecutionPolicy(workers=2, max_submissions=2),
        )
        pool = execution._executor()
        probes = (pool.submit(_terminal_worker_ready), pool.submit(_terminal_worker_ready))
        workers = [ready.get(timeout=30), ready.get(timeout=30)]
        gate.set()
        for probe in probes:
            probe.result(timeout=30)
        # Keep one worker active under the coordinator's cancellation owner while
        # its sibling returns to the real ProcessPoolExecutor call queue.
        submit = pool.submit
        cast(Any, pool).submit = lambda *_args: submit(_cooperative_from_initializer)
        handle = execution.submit_formal(execution.try_admit(), content)
        if not active.wait(30):
            raise TimeoutError("cooperative worker did not enter its request")
        ownership = _ownership(execution)
        channel.send({"ready": True, "workers": workers})
        interrupted = False
        try:
            signal.pause()
        except KeyboardInterrupt:
            interrupted = True
        before = time.monotonic()
        execution.close()
        elapsed = time.monotonic() - before
        with pytest.raises(CPURequestCancelled):
            handle.collect()
        _assert_retired(execution, ownership)
        channel.send(
            {
                "interrupted": interrupted,
                "elapsed": elapsed,
                "worker_exitcodes": [p.exitcode for p in ownership.processes],
                "physically_retired": execution._physical_retired,
            }
        )
    except BaseException as error:
        channel.send({"error": repr(error)})
        raise
    finally:
        if execution is not None:
            with suppress(BaseException):
                execution.close()
        if ready is not None:
            ready.close()
            ready.join_thread()
        channel.close()


@pytest.mark.skipif(not hasattr(os, "setsid"), reason="POSIX process-group delivery is required")
def test_terminal_group_sigint_keeps_worker_queue_and_coordinator_retirement_owned(prepared):
    # killpg exercises the same group delivery used by terminal Ctrl-C. This
    # control does not set up a controlling terminal or test shell job control.
    context = multiprocessing.get_context("spawn")
    parent, child = context.Pipe()
    process = context.Process(
        target=_terminal_group_coordinator,
        args=(child, cpu_execution.release_capsule(prepared), packet(prepared)),
    )
    process.start()
    pid = process.pid
    assert pid is not None
    child.close()
    try:
        assert parent.poll(45), "isolated coordinator did not prepare its CPU workers"
        started = parent.recv()
        assert started.get("ready"), started
        assert len({worker["pid"] for worker in started["workers"]}) == 2
        assert all(worker["group"] == pid for worker in started["workers"])
        os.killpg(pid, signal.SIGINT)
        assert parent.poll(15), "interrupted coordinator did not establish CPU retirement"
        result = parent.recv()
        assert "error" not in result, result
        assert result["interrupted"] and result["physically_retired"]
        assert all(worker["ignores_sigint"] for worker in started["workers"])
        assert result["worker_exitcodes"] == [0, 0]
        assert result["elapsed"] < _CLOSE_GRACE + _EXIT_GRACE + _SCHEDULING_SLACK
        process.join(15)
        assert process.exitcode == 0
    finally:
        # A failed control cannot leave descendants outside the pytest owner.
        with suppress(ProcessLookupError):
            if os.getpgid(pid) == pid:
                os.killpg(pid, signal.SIGKILL)
        if process.is_alive():
            process.kill()
        process.join(15)
        parent.close()
