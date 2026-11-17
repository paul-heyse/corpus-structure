"""Real process placement and private CPU boundary failures, independent source expectations."""

import json
import os
from collections.abc import Callable
from concurrent.futures import Future
from hashlib import sha256
from typing import cast

import pytest

from corpus_structure.core.execution_policy import CharacterizationExecutionPolicy
from corpus_structure.semantic.cpu_execution import (
    CapacityExceeded,
    CPUExecutionScope,
    CPUReply,
    OwnedByteBudget,
    hydrate_capsule,
    release_capsule,
)
from corpus_structure.semantic.identity import canonical_bytes
from semantic.cpu_execution_support import execute_formal
from semantic.cpu_execution_support import packet as packet
from semantic.cpu_execution_support import prepared as prepared


def test_real_worker_main_thread_warm_process_and_source_exactness(prepared):
    execution = CPUExecutionScope(
        prepared, CharacterizationExecutionPolicy(workers=1, max_submissions=1)
    )
    try:
        with execute_formal(execution, packet(prepared), lambda: None) as first:
            first_pid = first.pid
            assert first_pid != os.getpid() and first.main_thread
            assert first.native_thread_limit == 1
            assert first.native_pools
            assert all(pool["num_threads"] == 1 for pool in first.native_pools)
            assert execution.native_thread_reports[first_pid]["pools"] == first.native_pools
            assert first.execution_receipt.result_digest == sha256(first.content).hexdigest()
            layer = json.loads(first.content)
            assert any(
                extent["text"] == "x≥2"
                for packet in layer["members"]
                if packet["body"]["record_type"] == "occurrence"
                for extent in packet["body"]["extents"]
            )
            assert execution.budget.used_bytes > len(first.content)
        with execute_formal(execution, packet(prepared), lambda: None) as second:
            assert second.pid == first_pid
    finally:
        execution.close()
    assert execution.budget.used_bytes == 0


def test_capsule_tampering_and_malformed_packet_refuse(prepared):
    capsule = json.loads(release_capsule(prepared))
    capsule["products"]["release_id"] = "release:" + "0" * 64
    with pytest.raises(ValueError, match="identity"):
        hydrate_capsule(canonical_bytes(capsule))
    execution = CPUExecutionScope(prepared)
    try:
        with pytest.raises(ValueError), execute_formal(execution, b"{}", lambda: None):
            pytest.fail("malformed packet produced a layer")
    finally:
        execution.close()
    assert execution.budget.used_bytes == 0


def test_finite_policy_and_encoded_capacity():
    with pytest.raises(ValueError):
        CharacterizationExecutionPolicy(workers=True)
    with pytest.raises(ValueError):
        CharacterizationExecutionPolicy(max_submissions=0)
    budget = OwnedByteBudget(10)
    budget.reserve(7)
    with pytest.raises(CapacityExceeded):
        budget.reserve(4)
    assert budget.used_bytes == 7
    budget.release(7)
    assert budget.used_bytes == 0


def test_packet_limit_and_real_inflight_cancellation_release_owned_capacity(prepared, monkeypatch):
    import multiprocessing

    policy = CharacterizationExecutionPolicy(max_packet_bytes=64)
    execution = CPUExecutionScope(prepared, policy)
    try:
        with (
            pytest.raises(CapacityExceeded),
            execute_formal(execution, packet(prepared), lambda: None),
        ):
            pytest.fail("oversized input was submitted")
    finally:
        execution.close()
    assert execution.budget.used_bytes == 0
    execution = CPUExecutionScope(prepared)
    try:
        with multiprocessing.get_context("spawn").Manager() as manager:
            started, release = manager.Event(), manager.Event()
            pool = execution._executor()
            submit = cast(Callable[..., Future[CPUReply]], pool.submit)
            submissions = 0

            def submit_gated(fn, *args):
                nonlocal submissions
                submissions += 1
                if submissions == 1:
                    return submit(_gated_compute, *args, started, release)
                return submit(fn, *args)

            monkeypatch.setattr(pool, "submit", submit_gated)

            def cancel_while_waiting():
                if started.is_set():
                    raise RuntimeError("lost exact claim")

            try:
                with (
                    pytest.raises(RuntimeError, match="lost exact claim"),
                    execute_formal(
                        execution, _identified_packet(prepared, "slow"), cancel_while_waiting
                    ),
                ):
                    pytest.fail("cancelled claim returned a usable result")
                assert started.is_set(), "cancellation did not reach the running child"
                assert not execution._stop.is_set()
            finally:
                release.set()
            with execute_formal(execution, packet(prepared), lambda: None) as sibling:
                assert sibling.content
    finally:
        execution.close()
    assert execution.budget.used_bytes == 0


def test_broken_worker_initializer_is_terminal_and_releases_capacity(prepared, monkeypatch):
    from corpus_structure.semantic import cpu_execution

    monkeypatch.setattr(cpu_execution, "release_capsule", lambda _: b"{}")
    execution = CPUExecutionScope(prepared)
    try:
        with (
            pytest.raises(Exception, match=r"terminated|initializer"),
            execute_formal(execution, packet(prepared), lambda: None),
        ):
            pytest.fail("invalid initializer produced a layer")
    finally:
        execution.close()
    assert execution.budget.used_bytes == 0


def _raise_timeout():
    raise TimeoutError("kernel timeout sentinel")


def _wrong_reply():
    from corpus_structure.semantic.cpu_execution import CPUReply

    return CPUReply("wrong-request", b"{}", os.getpid(), True)


@pytest.mark.parametrize(
    "worker, message",
    [
        (_raise_timeout, "kernel timeout sentinel"),
        (_wrong_reply, "request/main-thread"),
    ],
)
def test_actual_child_error_and_misrouted_reply_are_not_polling_waits(
    prepared, monkeypatch, worker, message
):
    execution = CPUExecutionScope(prepared)
    try:
        pool = execution._executor()
        submit = cast(Callable[..., Future[CPUReply]], pool.submit)
        monkeypatch.setattr(pool, "submit", lambda *_args: submit(worker))
        with (
            pytest.raises((TimeoutError, ValueError), match=message),
            execute_formal(execution, packet(prepared), lambda: None),
        ):
            pytest.fail("invalid child completion was accepted")
    finally:
        execution.close()
    assert execution.budget.used_bytes == 0


def _gated_compute(
    content, max_reply_bytes, slot, generation, profile, stream_connection, capsule, started, release
):
    from time import monotonic

    from corpus_structure.semantic import cpu_execution

    cpu_execution._WORKER_REQUEST = (slot, generation)
    if json.loads(content.content)["request_id"] == "slow":
        started.set()
        deadline = monotonic() + 60
        while not release.wait(0.05):
            cpu_execution._worker_active()
            if monotonic() > deadline:
                raise RuntimeError("test synchronization did not release CPU worker")
    return cpu_execution._dispatch(
        content, max_reply_bytes, slot, generation, profile, stream_connection, capsule
    )


def _identified_packet(prepared, identity):
    value = json.loads(packet(prepared))
    value["request_id"] = identity
    return canonical_bytes(value)


def _collect(execution, content):
    with execute_formal(execution, content, lambda: None) as reply:
        return reply


def test_two_real_workers_complete_out_of_order_without_crossing_requests(prepared, monkeypatch):
    import multiprocessing
    from concurrent.futures import ThreadPoolExecutor
    from hashlib import sha256

    policy = CharacterizationExecutionPolicy(workers=2, max_submissions=2)
    execution = CPUExecutionScope(prepared, policy)
    try:
        with multiprocessing.get_context("spawn").Manager() as manager:
            started, release = manager.Event(), manager.Event()
            pool = execution._executor()
            submit = cast(Callable[..., Future[CPUReply]], pool.submit)
            monkeypatch.setattr(
                pool, "submit", lambda _fn, *args: submit(_gated_compute, *args, started, release)
            )
            slow, fast = _identified_packet(prepared, "slow"), _identified_packet(prepared, "fast")
            with ThreadPoolExecutor(max_workers=2) as callers:
                left = callers.submit(_collect, execution, slow)
                assert started.wait(60), "first worker did not reach synchronization point"
                try:
                    right = callers.submit(_collect, execution, fast)
                    quick = right.result(timeout=60)
                    assert not left.done()
                    assert quick.request_digest == sha256(fast).hexdigest()
                finally:
                    release.set()
                delayed = left.result(timeout=60)
                assert delayed.request_digest == sha256(slow).hexdigest()
                assert delayed.pid != quick.pid
                assert json.loads(delayed.content) == json.loads(quick.content)
    finally:
        execution.close()
    assert execution.budget.used_bytes == 0


def test_transient_byte_saturation_backpressures_before_second_submission(prepared, monkeypatch):
    import multiprocessing
    import threading
    from concurrent.futures import ThreadPoolExecutor

    slow, fast = _identified_packet(prepared, "slow"), _identified_packet(prepared, "fast")
    capsule_bytes = len(release_capsule(prepared))
    policy = CharacterizationExecutionPolicy(
        workers=2,
        max_submissions=2,
        max_packet_bytes=len(slow),
        max_reply_bytes=8 * 1024**2,
        max_native_request_bytes=1,
        max_native_reply_bytes=1,
        max_owned_bytes=capsule_bytes + len(slow) + 8 * 1024**2,
    )
    execution = CPUExecutionScope(prepared, policy)
    saturated = threading.Event()
    reserve = execution.budget.reserve

    def observe_reservation(size):
        try:
            reserve(size)
        except CapacityExceeded:
            saturated.set()
            raise

    try:
        with multiprocessing.get_context("spawn").Manager() as manager:
            started, release = manager.Event(), manager.Event()
            pool = execution._executor()
            submit = cast(Callable[..., Future[CPUReply]], pool.submit)
            submitted = []

            def submit_gated(_fn, *args):
                submitted.append(json.loads(args[0])["request_id"])
                return submit(_gated_compute, *args, started, release)

            monkeypatch.setattr(pool, "submit", submit_gated)
            monkeypatch.setattr(execution.budget, "reserve", observe_reservation)
            with ThreadPoolExecutor(max_workers=2) as callers:
                left = callers.submit(_collect, execution, slow)
                assert started.wait(60)
                try:
                    right = callers.submit(_collect, execution, fast)
                    assert saturated.wait(60), "second input did not encounter occupied byte budget"
                    assert submitted == ["slow"]
                    assert not right.done()
                    assert execution.budget.used_bytes <= policy.max_owned_bytes
                finally:
                    release.set()
                left.result(timeout=60)
                right.result(timeout=60)
                assert submitted == ["slow", "fast"]
    finally:
        execution.close()
    assert execution.budget.used_bytes == 0


def test_async_independent_cancel_generation_reuse_and_reply_retention(prepared, monkeypatch):
    import multiprocessing

    from corpus_structure.semantic.cpu_execution import CPURequestCancelled

    execution = CPUExecutionScope(prepared)
    try:
        with multiprocessing.get_context("spawn").Manager() as manager:
            started, release = manager.Event(), manager.Event()
            pool = execution._executor()
            submit = cast(Callable[..., Future[CPUReply]], pool.submit)
            monkeypatch.setattr(
                pool, "submit", lambda _fn, *args: submit(_gated_compute, *args, started, release)
            )
            slow_permit = execution.try_admit()
            fast_permit = execution.try_admit()
            assert slow_permit is not None and fast_permit is not None
            assert execution.try_admit() is None
            slow = execution.submit_formal(slow_permit, _identified_packet(prepared, "slow"))
            assert started.wait(60)
            assert execution.collect(slow) is None
            fast = execution.submit_formal(fast_permit, _identified_packet(prepared, "fast"))
            fast.future.result(timeout=60)
            reply = fast.collect()
            assert fast_permit.reserved == len(reply.content)
            replacement = execution.try_admit()
            assert replacement is not None
            assert replacement.slot == fast_permit.slot
            assert replacement.generation > fast_permit.generation
            fast.cancel()
            assert execution._cancellation[replacement.slot * 2 + 1] == 0
            next_job = execution.submit_formal(replacement, _identified_packet(prepared, "next"))
            slow.cancel()
            with pytest.raises(CPURequestCancelled):
                slow.future.result(timeout=60)
            with pytest.raises(CPURequestCancelled):
                slow.collect()
            assert slow.retire()
            next_job.future.result(timeout=60)
            assert next_job.collect().content
            assert not execution._stop.is_set()
            assert next_job.retire()
            assert fast.retire()
    finally:
        execution.close()
    assert execution.budget.used_bytes == 0


def test_owned_dispatch_carries_sealed_packet_digest_without_rehashing(monkeypatch):
    from corpus_structure.semantic import cpu_execution, data_operation_cpu

    packet = cpu_execution._SealedPacket.seal(b"exact physical request")
    expected = packet.digest

    def forbidden(*args, **kwargs):
        raise AssertionError("worker rehashed established request bytes")

    monkeypatch.setattr(cpu_execution, "sha256", forbidden)
    monkeypatch.setattr(cpu_execution, "_worker_active", lambda: None)
    monkeypatch.setattr(cpu_execution, "_apply_native_thread_limits", lambda: None)
    monkeypatch.setattr(
        data_operation_cpu, "execute_python_call", lambda *args, **kwargs: b"result"
    )
    reply = cpu_execution._dispatch(packet, 1024, -1, 0, "closed-python")
    assert reply.request_digest == expected
    assert reply.content == b"result"
