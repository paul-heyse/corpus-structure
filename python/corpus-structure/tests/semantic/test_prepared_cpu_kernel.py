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


def captured_kernel(tmp_path, monkeypatch):
    name = "prepared_kernel_" + tmp_path.name.replace("-", "_")
    content = (
        "def kernel(value: int, *, check_active) -> dict[str, float]:\n"
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
                kernel, bound, sources,
                execution_owner=SimpleNamespace(cpu=cpu, reservation=None),
                check_active=lambda: None,
            ),
            lambda: None,
        )
        assert result.value == {"answer": 4.25}
        assert type(result.value["answer"]) is float
        assert json.loads(result.cpu_execution_evidence)["pid"] != os.getpid()
        assert acquired.verifications >= 3
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
        if checked >= 3:
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
