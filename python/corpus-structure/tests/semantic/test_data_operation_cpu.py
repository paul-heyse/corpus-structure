"""Actual spawned closed Python calls share bounded CPU custody and exact types."""

import copy
import json
import os
import time
from dataclasses import replace
from types import SimpleNamespace
from typing import cast

import pytest
from pydantic import ValidationError

from corpus_structure.core.execution_policy import CharacterizationExecutionPolicy
from corpus_structure.core.work import drive_prepared_work
from corpus_structure.semantic.cpu_execution import CPUExecutionScope
from corpus_structure.semantic.data_operation_compilation import compile_data_operations
from corpus_structure.semantic.data_operation_ports import (
    PortRefusal,
    PythonBatchMember,
    PythonRoleValue,
    resolve_python_port,
)
from corpus_structure.semantic.identity import claim_source_item__data_operation__
from corpus_structure.semantic.python_operation_sources import PythonSource, PythonSourceCollection
from corpus_structure.semantic.types import PreparedRelease

from .test_data_operation_ports import fixture_source, kind


def scope():
    return CPUExecutionScope(
        cast(PreparedRelease, SimpleNamespace(release_id="test:no-schema-capsule")),
        CharacterizationExecutionPolicy(workers=1, max_submissions=1),
        retain_schema=False,
    )


def run(port, cpu, values):
    return drive_prepared_work(
        port.plan_python(
            values,
            execution_owner=SimpleNamespace(cpu=cpu, reservation=None),
        ),
        lambda: None,
    )


def test_spawned_original_function_retains_exact_type_result_and_physical_receipt(
    tmp_path, monkeypatch
):
    model, sources = fixture_source(tmp_path, monkeypatch, "index: int", "return str(index + 1)")
    permissions = []
    port = resolve_python_port(
        model, sources, model.operations[0].semantic_id, authorize=permissions.append
    )
    assert port.native_selections == ()
    assert port.cpu_descriptor is not None
    # Exact source + owning node IDs; no complete model or PreparedRelease packet.
    packet = port.cpu_descriptor.packet({"index": 7}, port.signature)
    assert "model" not in json.loads(packet) and "schema" not in json.loads(packet)
    assert set(json.loads(packet)["expected_nodes"]) == {
        node.id.removeprefix("python:")
        for implementation in model.implementation_slices
        if implementation.root == port.operation.implementation_root
        for node in implementation.nodes
        if node.id.startswith("python:")
    }
    cpu = scope()
    try:
        result = run(port, cpu, (PythonRoleValue("index", kind(model, "index"), 7),))
        assert result.outputs[0].value() == "8"
        assert result.outputs[0].kind_contract == kind(model, "address")
        evidence = json.loads(result.cpu_execution_evidence)
        assert evidence["pid"] != os.getpid() and evidence["main_thread"] is True
        assert evidence["native_thread_limit"] == 1
        assert cpu._capsule_bytes == 0
        assert len(permissions) >= 2
        with pytest.raises(ValidationError):
            run(port, cpu, (PythonRoleValue("index", kind(model, "index"), True),))
    finally:
        cpu.close()
    assert cpu.budget.used_bytes == 0


def test_spawned_stateless_inherited_receiver_uses_actual_class_and_captured_constants(
    tmp_path, monkeypatch
):
    metadata = copy.deepcopy(claim_source_item__data_operation__)
    metadata["entrypoints"] = ["run"]
    name = "cpu_receiver_" + tmp_path.name.replace("-", "_")
    source = (
        "class Base:\n    prefix = 'base:'\n"
        "    def run(self, index: int) -> str: return self.prefix + str(index)\n"
        "class Child(Base):\n    prefix = 'child:'\n"
        f"Child.__data_operation__ = {metadata!r}\n"
    )
    path = tmp_path / (name + ".py")
    path.write_text(source)
    monkeypatch.syspath_prepend(str(tmp_path))
    sources = PythonSourceCollection((PythonSource(name, source.encode(), str(path)),))
    model = compile_data_operations(python_sources=sources)
    port = resolve_python_port(
        model, sources, model.operations[0].semantic_id, authorize=lambda _: None
    )
    cpu = scope()
    try:
        result = run(port, cpu, (PythonRoleValue("index", kind(model, "index"), 3),))
        assert result.outputs[0].value() == "child:3"
    finally:
        cpu.close()


def test_spawned_original_batch_retains_exact_logical_order_and_one_cpu_receipt(
    tmp_path, monkeypatch
):
    metadata = copy.deepcopy(claim_source_item__data_operation__)
    metadata["capabilities"]["forms"] = ["batch"]
    model, sources = fixture_source(
        tmp_path,
        monkeypatch,
        "index: tuple[int, ...]",
        "return tuple(str(value) for value in index)",
        metadata=metadata,
        returns="tuple[str, ...]",
    )
    port = resolve_python_port(
        model, sources, model.operations[0].semantic_id, authorize=lambda _: None
    )
    members = tuple(
        PythonBatchMember(name, (PythonRoleValue("index", kind(model, "index"), value),))
        for name, value in (("second", 2), ("first", 1))
    )
    cpu = scope()
    try:
        result = drive_prepared_work(
            port.plan_batch_python(
                members,
                execution_owner=SimpleNamespace(cpu=cpu, reservation=None),
            ),
            lambda: None,
        )
        assert [(name, completion.outputs[0].value()) for name, completion in result.members] == [
            ("second", "2"),
            ("first", "1"),
        ]
        assert len({completion.cpu_execution_evidence for _, completion in result.members}) == 1
    finally:
        cpu.close()


def test_parent_and_child_refuse_changed_captured_source(tmp_path, monkeypatch):
    model, sources = fixture_source(tmp_path, monkeypatch)
    port = resolve_python_port(
        model, sources, model.operations[0].semantic_id, authorize=lambda _: None
    )
    assert port.cpu_descriptor is not None
    packet = port.cpu_descriptor.packet({"index": 7}, port.signature)
    path = tmp_path / (sources.sources[0].module + ".py")
    path.write_bytes(path.read_bytes() + b"\n# replaced after admission\n")
    cpu = scope()
    try:
        with pytest.raises(PortRefusal, match="source changed"):
            run(port, cpu, ())
        admission = cpu.try_admit(lambda: None)
        assert admission is not None
        handle = cpu.submit_closed_python(admission, packet)
        handle.future.result(timeout=60)
        with pytest.raises(RuntimeError, match="source differs"):
            handle.collect()
        assert handle.retire()
    finally:
        cpu.close()
    assert cpu.budget.used_bytes == 0


def test_hung_original_call_cancellation_drains_actual_cpu_process(tmp_path, monkeypatch):
    from corpus_structure.semantic import cpu_execution

    model, sources = fixture_source(
        tmp_path,
        monkeypatch,
        "index: int",
        "while index:\n        index += 1\n    return str(index)",
    )
    port = resolve_python_port(
        model, sources, model.operations[0].semantic_id, authorize=lambda _: None
    )
    assert port.cpu_descriptor is not None
    cpu = scope()
    monkeypatch.setattr(cpu_execution, "_COOPERATIVE_CLOSE_SECONDS", 0.1)
    monkeypatch.setattr(cpu_execution, "_WORKER_EXIT_SECONDS", 2.0)
    admission = cpu.try_admit(lambda: None)
    assert admission is not None
    handle = cpu.submit_closed_python(
        admission, port.cpu_descriptor.packet({"index": 1}, port.signature)
    )
    deadline = time.monotonic() + 15
    while not handle.future.running() and time.monotonic() < deadline:
        time.sleep(0.01)
    assert handle.future.running()
    assert cpu._pool_ownership is not None
    processes = cpu._pool_ownership.processes
    handle.cancel()
    started = time.monotonic()
    cpu.close()
    assert time.monotonic() - started < 8
    assert all(not process.is_alive() for process in processes)
    assert cpu._physical_retired and cpu.budget.used_bytes == 0


def test_prepared_kernel_profile_reuses_exact_same_cpu_owner_and_parent_validation(
    tmp_path, monkeypatch
):
    from corpus_structure.semantic.data_operation_cpu import plan_cpu_call

    model, sources = fixture_source(tmp_path, monkeypatch, "index: int", "return str(index * 2)")
    port = resolve_python_port(
        model, sources, model.operations[0].semantic_id, authorize=lambda _: None
    )
    assert port.cpu_descriptor is not None
    descriptor = replace(port.cpu_descriptor, verification="prepared-kernel", expected_nodes=())
    verified = []

    def verify():
        port.verify_runtime()
        verified.append(True)

    cpu = scope()
    try:
        reply = drive_prepared_work(
            plan_cpu_call(
                descriptor,
                port.signature.bind(index=9),
                port.signature,
                verify=verify,
                execution_owner=SimpleNamespace(cpu=cpu, reservation=None),
                check_active=lambda: None,
            ),
            lambda: None,
        )
        assert reply.content == b'"18"' and reply.pid != os.getpid()
        assert len(verified) == 3
        assert cpu._capsule_bytes == 0
    finally:
        cpu.close()
    assert cpu.budget.used_bytes == 0


def test_prepared_kernel_injects_only_owned_cooperative_control(tmp_path, monkeypatch):
    import importlib
    import inspect

    from corpus_structure.semantic.data_operation_cpu import PythonCPUDescriptor, plan_cpu_call

    name = "controlled_kernel_" + tmp_path.name.replace("-", "_")
    source = ("from collections.abc import Callable\n"
              "def run(value: int, *, check_active: Callable[[], None]) -> str:\n"
              "    check_active()\n    return str(value + 3)\n")
    path = tmp_path / (name + ".py")
    path.write_text(source)
    monkeypatch.syspath_prepend(str(tmp_path))
    function = importlib.import_module(name).run
    signature = inspect.signature(function)
    descriptor = PythonCPUDescriptor(
        ((name, str(path), source.encode()),), name + ".run", (),
        verification="prepared-kernel", control_parameter="check_active",
    )
    bound = signature.bind(value=4, check_active=lambda: None)
    packet = json.loads(descriptor.packet(bound.arguments, signature))
    assert packet["arguments"] == {"value": "4"}
    with pytest.raises(ValueError, match="only prepared kernels"):
        replace(descriptor, verification="closed-slice")
    cpu = scope()
    try:
        reply = drive_prepared_work(plan_cpu_call(
            descriptor, bound, signature, verify=lambda: None,
            execution_owner=SimpleNamespace(cpu=cpu, reservation=None), check_active=lambda: None,
        ), lambda: None)
        assert reply.content == b'"7"'
    finally:
        cpu.close()
