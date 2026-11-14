"""Original CPU continuations exchange nominal messages without replay or new pools."""

import importlib
import inspect
import os
from types import SimpleNamespace

import pytest

from corpus_structure.core.work import drive_prepared_work
from corpus_structure.semantic.data_operation_cpu import (
    PythonCPUDescriptor,
    _bound_arguments,
    _Call,
)
from corpus_structure.semantic.data_operation_stream import plan_cpu_coroutine
from semantic.data_operation_port_support import scope

SOURCE = """from collections.abc import Callable, Generator
from dataclasses import dataclass
from typing import Literal
import os

@dataclass(frozen=True)
class Question:
    value: int

@dataclass(frozen=True)
class Reply:
    value: int
    disposition: Literal["answer", "refused"] = "answer"

@dataclass(frozen=True)
class Result:
    total: int
    pid: int
    disposition: str

def interact(count: int, hang: bool, check_active: Callable[[], None]) -> Generator[Question, Reply, Result]:
    total = 0
    for value in range(count):
        check_active()
        reply = yield Question(value + 1)
        if reply.disposition == "refused":
            return Result(total, os.getpid(), "refused")
        total += reply.value
        if hang:
            while True:
                pass
    return Result(total, os.getpid(), "complete")
"""


def acquire(tmp_path, monkeypatch):
    name = "coroutine_" + tmp_path.name.replace("-", "_")
    path = tmp_path / (name + ".py")
    path.write_text(SOURCE)
    monkeypatch.syspath_prepend(str(tmp_path))
    module = importlib.import_module(name)
    signature = inspect.signature(module.interact, eval_str=True)
    descriptor = PythonCPUDescriptor(
        ((name, str(path), SOURCE.encode()),),
        name + ".interact",
        (),
        verification="prepared-kernel",
        control_parameter="check_active",
        invocation_form="coroutine",
    )
    return module, signature, descriptor


@pytest.mark.parametrize("refuse", [False, True])
def test_original_cpu_coroutine_typed_exchange_and_domain_refusal(tmp_path, monkeypatch, refuse):
    module, signature, descriptor = acquire(tmp_path, monkeypatch)
    cpu, questions = scope(), []

    def answer(question):
        questions.append(question.value)
        if False:
            yield ()
        return module.Reply(question.value * 10, "refused" if refuse else "answer")

    try:
        result, receipt = drive_prepared_work(
            plan_cpu_coroutine(
                descriptor,
                signature.bind(2, False, lambda: None),
                signature,
                verify=lambda: None,
                execution_owner=SimpleNamespace(cpu=cpu, reservation=None),
                check_active=lambda: None,
                answer_plan=answer,
            ),
            lambda: None,
        )
        assert questions == ([1] if refuse else [1, 2])
        assert result.total == (0 if refuse else 30)
        assert result.disposition == ("refused" if refuse else "complete")
        assert result.pid != os.getpid() and result.pid == receipt.execution_receipt.pid
        assert cpu._pool_ownership is not None
        assert len(cpu._pool_ownership.processes) == 1
    finally:
        cpu.close()
    assert cpu.budget.used_bytes == 0 and not cpu._stream_transports


@pytest.mark.parametrize("failure", ["invalid-reply", "cancel-hung-continuation"])
def test_cpu_coroutine_refuses_untyped_reply_and_cancels_hung_continuation(
    tmp_path, monkeypatch, failure
):
    import time

    from corpus_structure.semantic import cpu_execution

    module, signature, descriptor = acquire(tmp_path, monkeypatch)
    deadline = []

    def active():
        if deadline and time.monotonic() > deadline[0]:
            raise RuntimeError("cancel coroutine")

    def answer(question):
        if False:
            yield ()
        if failure == "invalid-reply":
            return {"value": 10}  # copied fields do not constitute the nominal reply
        deadline.append(time.monotonic() + 0.2)
        return module.Reply(10)

    monkeypatch.setattr(cpu_execution, "_COOPERATIVE_CLOSE_SECONDS", 0.01)
    monkeypatch.setattr(cpu_execution, "_WORKER_EXIT_SECONDS", 1)
    cpu, processes = scope(), ()
    try:
        with pytest.raises(Exception, match=r"Reply|cancel coroutine"):
            drive_prepared_work(
                plan_cpu_coroutine(
                    descriptor,
                    signature.bind(2, failure != "invalid-reply", active),
                    signature,
                    verify=lambda: None,
                    execution_owner=SimpleNamespace(cpu=cpu, reservation=None),
                    check_active=active,
                    answer_plan=answer,
                ),
                active,
            )
        assert cpu._pool_ownership is not None
        processes = cpu._pool_ownership.processes
    finally:
        cpu.close()
    assert all(not process.is_alive() for process in processes)
    assert cpu.budget.used_bytes == 0 and not cpu._stream_transports


def test_cpu_prepared_argument_is_exact_existing_worker_capsule_not_a_wire_object():
    def kernel(value: int, prepared):
        return value

    signature = inspect.signature(kernel)
    descriptor = PythonCPUDescriptor(
        (),
        "test.kernel",
        (),
        verification="prepared-kernel",
        prepared_parameter="prepared",
        prepared_release_id="release:one",
    )
    packet = descriptor.packet({"value": 7, "prepared": object()}, signature)
    call = _Call.model_validate_json(packet, strict=True)
    assert set(call.arguments) == {"value"}
    original = SimpleNamespace(release_id="release:one")
    bound = _bound_arguments(call, signature, lambda: None, {"release:one": original})
    assert bound.arguments == {"value": 7, "prepared": original}
    with pytest.raises(ValueError, match="exact admitted"):
        _bound_arguments(call, signature, lambda: None, {"release:other": original})
