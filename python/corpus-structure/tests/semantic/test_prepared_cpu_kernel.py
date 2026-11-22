"""Family-bound prepared kernels retain acquired verification and physical receipts."""

import importlib
import os
from types import SimpleNamespace

import pytest

from corpus_structure.core.work import drive_prepared_work
from corpus_structure.semantic.data_operation_prepared_call import PreparedOriginalCallPort
from corpus_structure.semantic.python_operation_sources import PythonSource, PythonSourceCollection
from semantic.data_operation_port_support import scope


class AcquiredPort(PreparedOriginalCallPort):
    def __init__(self):
        self.verifications = 0

    def _verify(self):
        self.verifications += 1


def captured_kernel(tmp_path, monkeypatch, *, sequence=False):
    name = "prepared_kernel_" + tmp_path.name.replace("-", "_")
    content = (
        "def kernel(value: int, *, check_active) -> tuple[float, ...]:\n"
        "    check_active()\n"
        "    return (value + 0.25, value - 0.5, value + 0.25)\n"
        if sequence
        else "def kernel(value: int, *, check_active) -> dict[str, float]:\n"
        "    check_active()\n"
        "    return {'answer': value + 0.25}\n"
    )
    path = tmp_path / (name + ".py")
    path.write_text(content)
    monkeypatch.syspath_prepend(str(tmp_path))
    kernel = importlib.import_module(name).kernel
    sources = PythonSourceCollection((PythonSource(name, content.encode(), str(path)),))
    return kernel, sources


def test_prepared_family_kernel_executes_in_shared_cpu_owner_with_verified_float_result(
    tmp_path, monkeypatch
):
    import inspect
    import json

    kernel, sources = captured_kernel(tmp_path, monkeypatch)
    bound = inspect.signature(kernel).bind(4, check_active=lambda: None)
    acquired = AcquiredPort()
    cpu = scope()
    try:
        result = drive_prepared_work(
            acquired.plan_cpu(
                kernel,
                bound,
                sources,
                execution_owner=SimpleNamespace(cpu=cpu, reservation=None),
                check_active=lambda: None,
            ),
            lambda: None,
        )
        assert result.value == {"answer": 4.25}
        assert type(result.value["answer"]) is float
        assert json.loads(result.cpu_execution_evidence)["pid"] != os.getpid()
        assert acquired.verifications == 2
    finally:
        cpu.close()
    assert cpu.budget.used_bytes == 0


def test_prepared_family_verification_can_refuse_a_collected_kernel_result(tmp_path, monkeypatch):
    import inspect

    kernel, sources = captured_kernel(tmp_path, monkeypatch)
    acquired = AcquiredPort()
    checked = 0

    def family_verify():
        nonlocal checked
        checked += 1
        if checked == 2:
            raise ValueError("family asset no longer matches acquisition")

    cpu = scope()
    try:
        with pytest.raises(ValueError, match="family asset no longer matches acquisition"):
            drive_prepared_work(
                acquired.plan_cpu(
                    kernel,
                    inspect.signature(kernel).bind(4, check_active=lambda: None),
                    sources,
                    verify=family_verify,
                    execution_owner=SimpleNamespace(cpu=cpu, reservation=None),
                    check_active=lambda: None,
                ),
                lambda: None,
            )
    finally:
        cpu.close()
    assert cpu.budget.used_bytes == 0


def test_prepared_eager_sequence_preserves_one_actual_whole_cpu_reply_and_receipt(
    tmp_path, monkeypatch
):
    import inspect
    import json
    from hashlib import sha256

    from corpus_structure.semantic.data_operation_ports import PythonRoleValue, resolve_python_port
    from corpus_structure.semantic.data_operation_prepared_call import PreparedCallResult
    from corpus_structure.semantic.identity import canonical_bytes
    from semantic.data_operation_port_support import (
        controlled_port_declaration,
        fixture_source,
        kind,
    )

    kernel, captured = captured_kernel(tmp_path, monkeypatch, sequence=True)
    declaration = controlled_port_declaration()
    declaration["roles"][-1].update(kind="float", collection="sequence", minimum=3, maximum=3)
    model, sources = fixture_source(
        tmp_path,
        monkeypatch,
        "index: int",
        "return (index + 0.25, index - 0.5, index + 0.25)",
        returns="tuple[float, ...]",
        metadata=declaration,
    )
    port = resolve_python_port(
        model, sources, model.operations[0].semantic_id, authorize=lambda _: None
    )
    acquired = AcquiredPort()
    acquired.operation = port.operation
    acquired._port = port
    acquired.retain_cpu_reply = True
    observed = []

    def physical(arguments, *, binding, check_active, execution_owner):
        reply = yield from acquired.plan_cpu_reply(
            kernel,
            inspect.signature(kernel).bind(arguments.arguments["index"], check_active=check_active),
            captured,
            execution_owner=execution_owner,
            check_active=check_active,
        )
        observed.append(reply)
        return PreparedCallResult(
            tuple(json.loads(reply.content)),
            cpu_execution_evidence=canonical_bytes(reply.execution_receipt.record()),
            cpu_execution_reply=reply.content,
        )

    acquired.physical_plan = physical
    cpu = scope()
    try:
        completed = drive_prepared_work(
            acquired.plan_python(
                (PythonRoleValue("index", kind(model, "index"), 4),),
                execution_owner=SimpleNamespace(cpu=cpu, reservation=None),
            ),
            lambda: None,
        )
        assert [output.value() for output in completed.outputs] == [4.25, 3.5, 4.25]
        assert len(observed) == 1
        (reply,) = observed
        assert completed.cpu_execution_reply == reply.content
        assert completed.cpu_execution_evidence == canonical_bytes(reply.execution_receipt.record())
        receipt = json.loads(completed.cpu_execution_evidence)
        assert receipt["pid"] != os.getpid()
        assert receipt["result_digest"] == sha256(reply.content).hexdigest()
        assert json.loads(reply.content) == [4.25, 3.5, 4.25]
    finally:
        cpu.close()
    assert cpu.budget.used_bytes == 0
