"""Real process placement and private CPU boundary failures, independent source expectations."""

import json
import os
from collections.abc import Callable
from concurrent.futures import Future
from dataclasses import asdict
from typing import cast
from uuid import uuid4

import pytest
from methods.test_formal_evidence import inputs

from corpus_structure.semantic.cpu_execution import (
    CapacityExceeded,
    CPUExecutionPolicy,
    CPUExecutionScope,
    CPUReply,
    OwnedByteBudget,
    hydrate_capsule,
    release_capsule,
)
from corpus_structure.semantic.identity import canonical_bytes
from semantic.test_formal_evidence import prepared as prepared


def packet(prepared):
    unit, cfg, _ctx, operation = inputs(prepared)
    view = unit.run.reader.source_view(11)
    return canonical_bytes(
        dict(
            request_id=uuid4().hex,
            run_id=None,
            claims=[],
            method="text.formal_evidence",
            release_id=prepared.release_id,
            configuration=cfg.model_dump(mode="json"),
            operation=operation,
            document_id=unit.ref.unit_id,
            sources=[
                dict(
                    ref=asdict(view.ref),
                    text=view.text,
                    pieces=view.pieces,
                    items=view.items,
                    ancestors=view.ancestors,
                    health=view.health,
                    text_policy=None,
                    analysis_enabled=True,
                    integrated_context=None,
                )
            ],
            dependencies=[],
        )
    )


def test_real_worker_main_thread_warm_process_and_source_exactness(prepared):
    execution = CPUExecutionScope(prepared)
    try:
        with execution.execute(packet(prepared), {}, lambda: None) as first:
            first_pid = first.pid
            assert first_pid != os.getpid() and first.main_thread
            layer = json.loads(first.content)
            assert any(
                extent["text"] == "x≥2" for row in layer["occurrences"] for extent in row["extents"]
            )
            assert execution.budget.used_bytes > len(first.content)
        with execution.execute(packet(prepared), {}, lambda: None) as second:
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
        with pytest.raises(ValueError), execution.execute(b"{}", {}, lambda: None):
            pytest.fail("malformed packet produced a layer")
    finally:
        execution.close()
    assert execution.budget.used_bytes == 0


def test_finite_policy_and_encoded_capacity():
    with pytest.raises(ValueError):
        CPUExecutionPolicy(workers=True)
    with pytest.raises(ValueError):
        CPUExecutionPolicy(max_submissions=0)
    budget = OwnedByteBudget(10)
    budget.reserve(7)
    with pytest.raises(CapacityExceeded):
        budget.reserve(4)
    assert budget.used_bytes == 7
    budget.release(7)
    assert budget.used_bytes == 0


def test_packet_limit_and_real_inflight_cancellation_release_owned_capacity(prepared):
    policy = CPUExecutionPolicy(max_packet_bytes=64)
    execution = CPUExecutionScope(prepared, policy)
    try:
        with pytest.raises(CapacityExceeded), execution.execute(packet(prepared), {}, lambda: None):
            pytest.fail("oversized input was submitted")
    finally:
        execution.close()
    assert execution.budget.used_bytes == 0
    execution = CPUExecutionScope(prepared)
    checks = 0

    def cancel_while_waiting():
        nonlocal checks
        checks += 1
        if checks >= 3:
            raise RuntimeError("lost exact claim")

    try:
        with (
            pytest.raises(RuntimeError, match="lost exact claim"),
            execution.execute(packet(prepared), {}, cancel_while_waiting),
        ):
            pytest.fail("cancelled claim returned a usable result")
        assert execution._stop.is_set()
        with (
            pytest.raises(RuntimeError, match="closed"),
            execution.execute(packet(prepared), {}, lambda: None),
        ):
            pytest.fail("stopped operation admitted more work")
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
            execution.execute(packet(prepared), {}, lambda: None),
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
            execution.execute(packet(prepared), {}, lambda: None),
        ):
            pytest.fail("invalid child completion was accepted")
    finally:
        execution.close()
    assert execution.budget.used_bytes == 0


def _gated_compute(content, capsules, max_reply_bytes, started, release):
    from corpus_structure.semantic.cpu_execution import _compute

    if json.loads(content)["request_id"] == "slow":
        started.set()
        if not release.wait(60):
            raise RuntimeError("test synchronization did not release CPU worker")
    return _compute(content, capsules, max_reply_bytes)


def _identified_packet(prepared, identity):
    value = json.loads(packet(prepared))
    value["request_id"] = identity
    return canonical_bytes(value)


def _collect(execution, content):
    with execution.execute(content, {}, lambda: None) as reply:
        return reply


def test_two_real_workers_complete_out_of_order_without_crossing_requests(prepared, monkeypatch):
    import multiprocessing
    from concurrent.futures import ThreadPoolExecutor
    from hashlib import sha256

    policy = CPUExecutionPolicy(workers=2, max_submissions=2)
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
    policy = CPUExecutionPolicy(
        workers=2,
        max_submissions=2,
        max_packet_bytes=len(slow),
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


def test_full_slot_blocks_method_source_hydration_before_input_factory(prepared, monkeypatch):
    import threading
    from concurrent.futures import ThreadPoolExecutor
    from dataclasses import replace

    from corpus_structure.methods.formal_evidence import FormalEvidenceMethod

    unit, cfg, ctx, _operation = inputs(prepared)
    execution = CPUExecutionScope(prepared)
    monkeypatch.setattr(unit.run.reader, "cpu_execution", execution, raising=False)
    source_view = unit.run.reader.source_view
    hydrated, waiting = threading.Event(), threading.Event()
    checks = 0

    def read_source(identity):
        hydrated.set()
        return source_view(identity)

    def active():
        nonlocal checks
        checks += 1
        if checks >= 2:
            waiting.set()

    monkeypatch.setattr(unit.run.reader, "source_view", read_source)
    ctx = replace(ctx, check_active=active)
    try:
        with ThreadPoolExecutor(max_workers=1) as callers:
            with execution.admitted_inputs(lambda: None):
                pending = callers.submit(FormalEvidenceMethod().run, (unit,), cfg, ctx)
                assert waiting.wait(60)
                assert not hydrated.is_set()
                assert not pending.done()
            (result,) = pending.result(timeout=60)
            assert hydrated.is_set()
            assert result.characterization_layer is not None
    finally:
        execution.close()
    assert execution.budget.used_bytes == 0
