"""Captured capabilities and terminal settlement retain independent meaning."""

import copy
import importlib
import json
from dataclasses import replace
from hashlib import sha256

import pytest

from corpus_structure.semantic.data_operation_compilation import compile_data_operations
from corpus_structure.semantic.data_operation_consumers import resolve_prepared_factory
from corpus_structure.semantic.data_operation_model import (
    MODEL_VERSION,
    PREVIOUS_MODEL_VERSION,
    read_effective_data_operations,
)
from corpus_structure.semantic.identity import claim_source_item__data_operation__
from corpus_structure.semantic.python_operation_sources import PythonSource, PythonSourceCollection


def test_compiled_factory_is_captured_from_original_static_owner(tmp_path, monkeypatch):
    metadata = copy.deepcopy(claim_source_item__data_operation__)
    metadata["entrypoints"] = ["run"]
    metadata["capabilities"]["prepared_factory"] = "acquire_port"
    name = "captured_factory_" + tmp_path.name.replace("-", "_")
    source = (
        "class Operation:\n"
        "    def run(self, index: int) -> str: return str(index)\n"
        "    @staticmethod\n"
        '    def acquire_port(*args, **kwargs): return "captured"\n'
        f"Operation.__data_operation__ = {metadata!r}\n"
    )
    path = tmp_path / (name + ".py")
    path.write_text(source)
    monkeypatch.syspath_prepend(str(tmp_path))
    sources = PythonSourceCollection((PythonSource(name, source.encode(), str(path)),))
    model = compile_data_operations(python_sources=sources)
    operation = model.operations[0]
    assert model.version == MODEL_VERSION
    assert operation.capabilities.prepared_factory.entrypoint == name + ".Operation.acquire_port"
    assert (
        operation.capabilities.prepared_factory.source_digest == sha256(source.encode()).hexdigest()
    )
    acquired = resolve_prepared_factory(model, sources, operation.semantic_id)
    assert acquired() == "captured"
    monkeypatch.setattr(
        importlib.import_module(name).Operation, "acquire_port", staticmethod(lambda: "changed")
    )
    with pytest.raises(ValueError, match="rebound"):
        acquired()


def test_exact_v3_archive_read_has_no_current_execution_authority():
    model = compile_data_operations()
    previous = replace(model, version=PREVIOUS_MODEL_VERSION)
    content = previous.content
    reopened = read_effective_data_operations(content)
    assert reopened.content == content
    assert json.loads(content)["version"] == PREVIOUS_MODEL_VERSION
    with pytest.raises(ValueError, match="historical"):
        reopened.projection_graph("semantic-reference")


@pytest.mark.parametrize("count", [0, 2])
def test_owned_stream_has_only_terminal_completion_and_spawned_receipt(
    tmp_path, monkeypatch, count
):
    import os
    from types import SimpleNamespace

    from corpus_structure.core.work import drive_prepared_work
    from corpus_structure.semantic.data_operation_ports import PythonRoleValue, resolve_python_port
    from semantic.data_operation_port_support import fixture_source, kind, scope

    metadata = copy.deepcopy(claim_source_item__data_operation__)
    metadata["capabilities"]["forms"] = ["stream"]
    metadata["opaque"] = [
        {
            "reference": "collections.abc.Iterator",
            "contract": "python-iterator-annotation",
            "role": "annotation",
            "content_digest": "a" * 64,
        }
    ]
    metadata["capabilities"]["stream_settlement"] = {
        "mode": "terminal-atomic",
        "output_role": "address",
        "terminal_outcome": "addressed",
    }
    output = next(role for role in metadata["roles"] if role["direction"] == "output")
    output.update(collection="sequence", minimum=0, maximum=None, presence="optional")
    model, sources = fixture_source(
        tmp_path,
        monkeypatch,
        "index: int",
        "for value in range(index):\n        yield str(value)",
        metadata=metadata,
        header="from collections.abc import Iterator",
        returns="Iterator[str]",
    )
    port = resolve_python_port(
        model, sources, model.operations[0].semantic_id, authorize=lambda _: None
    )
    cpu = scope()
    try:
        completion = drive_prepared_work(
            port.plan_python(
                (PythonRoleValue("index", kind(model, "index"), count),),
                execution_owner=SimpleNamespace(cpu=cpu, reservation=None),
            ),
            lambda: None,
        )
        assert [value.value() for value in completion.outputs] == [
            str(value) for value in range(count)
        ]
        assert completion.outcome == "addressed"
        assert json.loads(completion.cpu_execution_evidence)["pid"] != os.getpid()
    finally:
        cpu.close()
    assert cpu.budget.used_bytes == 0


def test_no_future_submission_keeps_its_byte_credit_until_physical_retirement():
    from types import SimpleNamespace

    from corpus_structure.orchestrate.data_operations import _RequestExecution
    from corpus_structure.semantic.cpu_execution import OwnedByteBudget

    budget = OwnedByteBudget(32)
    reservation = budget.admit(32)

    class FailedSubmit:
        def submit(self, callback):
            raise RuntimeError("acknowledgement lost")

    invocation = SimpleNamespace(
        pool=FailedSubmit(),
        uncertain_python=[],
        cpu=None,
        native_hosts=None,
        executor=SimpleNamespace(engine=None),
    )
    owner = _RequestExecution(invocation, reservation)
    with pytest.raises(RuntimeError, match="acknowledgement lost"):
        owner.submit_python(lambda: None)
    reservation.release()
    assert budget.used_bytes == 32
    assert len(invocation.uncertain_python) == 1
    _, retained = invocation.uncertain_python[0]
    retained.release()  # confirmed physical teardown owner releases the remaining share
    assert budget.used_bytes == 0


def test_transport_pool_shutdown_is_bounded_and_reports_unproven_work(monkeypatch):
    from threading import Event

    from corpus_structure.core.work import PhysicalRetirementUncertain
    from corpus_structure.orchestrate.data_operations import _OwnedPythonPool
    from corpus_structure.semantic import cpu_execution

    monkeypatch.setattr(cpu_execution, "_COOPERATIVE_CLOSE_SECONDS", 0.01)
    monkeypatch.setattr(cpu_execution, "_WORKER_EXIT_SECONDS", 0.01)
    running, stop = Event(), Event()
    pool = _OwnedPythonPool(1)

    def blocked():
        running.set()
        stop.wait()

    pool.submit(blocked)
    assert running.wait(2)
    try:
        with pytest.raises(PhysicalRetirementUncertain, match="capacity remains owned"):
            pool.close()
        assert pool.drained is False
    finally:
        stop.set()
        pool.pool.shutdown(wait=True)


def test_invalid_stream_item_cannot_fulfill_its_valid_prefix(tmp_path, monkeypatch):
    from types import SimpleNamespace

    from corpus_structure.core.work import drive_prepared_work
    from corpus_structure.semantic.data_operation_ports import PythonRoleValue, resolve_python_port
    from semantic.data_operation_port_support import fixture_source, kind, scope

    metadata = copy.deepcopy(claim_source_item__data_operation__)
    metadata["capabilities"]["forms"] = ["stream"]
    metadata["opaque"] = [
        {
            "reference": "collections.abc.Iterator",
            "contract": "python-iterator-annotation",
            "role": "annotation",
            "content_digest": "a" * 64,
        }
    ]
    metadata["capabilities"]["stream_settlement"] = {
        "mode": "terminal-atomic",
        "output_role": "address",
        "terminal_outcome": "addressed",
    }
    output = next(role for role in metadata["roles"] if role["direction"] == "output")
    output.update(collection="sequence", minimum=0, maximum=None, presence="optional")
    model, sources = fixture_source(
        tmp_path,
        monkeypatch,
        "index: int",
        "yield str(index)\n    yield index",
        metadata=metadata,
        header="from collections.abc import Iterator",
        returns="Iterator[str]",
    )
    port = resolve_python_port(
        model, sources, model.operations[0].semantic_id, authorize=lambda _: None
    )
    cpu = scope()
    try:
        with pytest.raises(ValueError, match="string"):
            drive_prepared_work(
                port.plan_python(
                    (PythonRoleValue("index", kind(model, "index"), 5),),
                    execution_owner=SimpleNamespace(cpu=cpu, reservation=None),
                ),
                lambda: None,
            )
    finally:
        cpu.close()
    assert cpu.budget.used_bytes == 0


def test_cancelled_hung_pull_retires_the_owned_process_without_fulfilling_prefix(
    tmp_path, monkeypatch
):
    import time
    from types import SimpleNamespace

    from corpus_structure.core.work import drive_prepared_work
    from corpus_structure.semantic import cpu_execution, data_operation_stream
    from corpus_structure.semantic.data_operation_ports import PythonRoleValue, resolve_python_port
    from semantic.data_operation_port_support import fixture_source, kind, scope

    metadata = copy.deepcopy(claim_source_item__data_operation__)
    metadata["capabilities"]["forms"] = ["stream"]
    metadata["opaque"] = [
        {
            "reference": "collections.abc.Iterator",
            "contract": "python-iterator-annotation",
            "role": "annotation",
            "content_digest": "a" * 64,
        }
    ]
    metadata["capabilities"]["stream_settlement"] = {
        "mode": "terminal-atomic",
        "output_role": "address",
        "terminal_outcome": "addressed",
    }
    output = next(role for role in metadata["roles"] if role["direction"] == "output")
    output.update(collection="sequence", minimum=0, maximum=None, presence="optional")
    model, sources = fixture_source(
        tmp_path,
        monkeypatch,
        "index: int",
        "yield str(index)\n    while True:\n        pass",
        metadata=metadata,
        header="from collections.abc import Iterator",
        returns="Iterator[str]",
    )
    port = resolve_python_port(
        model, sources, model.operations[0].semantic_id, authorize=lambda _: None
    )
    original = data_operation_stream.OwnedCPUStream.pull
    deadline = []

    def observe_second_pull(stream):
        if stream.ordinal == 1:
            deadline.append(time.monotonic() + 0.2)
        return original(stream)

    def active():
        if deadline and time.monotonic() > deadline[0]:
            raise RuntimeError("cancel selected stream")

    monkeypatch.setattr(data_operation_stream.OwnedCPUStream, "pull", observe_second_pull)
    monkeypatch.setattr(cpu_execution, "_COOPERATIVE_CLOSE_SECONDS", 0.01)
    monkeypatch.setattr(cpu_execution, "_WORKER_EXIT_SECONDS", 1)
    cpu = scope()
    processes = ()
    try:
        with pytest.raises(RuntimeError, match="cancel selected stream"):
            drive_prepared_work(
                port.plan_python(
                    (PythonRoleValue("index", kind(model, "index"), 5),),
                    check_active=active,
                    execution_owner=SimpleNamespace(cpu=cpu, reservation=None),
                ),
                active,
            )
        assert deadline
        processes = cpu._pool_ownership.processes
        assert processes and any(process.is_alive() for process in processes)
    finally:
        cpu.close()
    assert all(not process.is_alive() for process in processes)
    assert cpu.budget.used_bytes == 0


def test_uncertain_stream_submit_closes_pipes_but_keeps_cpu_admission(monkeypatch):
    from corpus_structure.semantic.data_operation_stream import OwnedCPUStream
    from semantic.data_operation_port_support import scope

    cpu = scope()
    cpu.prepare()
    observed = []
    original_pipe = cpu._context.Pipe
    original_submit = cpu._pool.submit

    def pipe(*args, **kwargs):
        pair = original_pipe(*args, **kwargs)
        observed.extend(pair)
        return pair

    def uncertain(*args, **kwargs):
        original_submit(*args, **kwargs)
        raise RuntimeError("stream submit acknowledgement lost")

    monkeypatch.setattr(cpu._context, "Pipe", pipe)
    monkeypatch.setattr(cpu._pool, "submit", uncertain)
    admission = cpu.try_admit()
    assert admission is not None
    try:
        with pytest.raises(RuntimeError, match="acknowledgement lost"):
            OwnedCPUStream(cpu, admission, b"{}", lambda: None)
        assert len(observed) == 2 and all(connection.closed for connection in observed)
        assert admission.submitted and not admission.retired
        assert cpu.budget.used_bytes > 0
        with pytest.raises(RuntimeError, match="uncertain submission"):
            cpu._executor()
    finally:
        cpu.close()
    assert cpu.budget.used_bytes == 0


def test_captured_factory_rejects_rebound_imported_resolver_with_copied_identity(
    tmp_path, monkeypatch
):
    from types import SimpleNamespace

    from corpus_structure.semantic.data_operation_consumers import resolve_prepared_factory
    from corpus_structure.semantic.data_operation_ports import PortRefusal

    metadata = copy.deepcopy(claim_source_item__data_operation__)
    metadata["entrypoints"] = ["run"]
    metadata["capabilities"]["prepared_factory"] = "acquire_port"
    name = "factory_binding_" + tmp_path.name.replace("-", "_")
    helper_name = name + "_helper"
    helper = (
        "class Port:\n"
        "    def __init__(self, identity): self.identity = identity\n"
        "    def plan_python(self, *args, **kwargs): yield ()\n"
        "def resolve_port(identity): return Port(identity)\n"
    )
    source = (
        "class Operation:\n"
        "    def run(self, index: int) -> str: return str(index)\n"
        "    @staticmethod\n"
        "    def acquire_port(*, identity):\n"
        f"        from {helper_name} import resolve_port\n"
        "        return resolve_port(identity)\n"
        f"Operation.__data_operation__ = {metadata!r}\n"
    )
    inputs = []
    for module, body in ((name, source), (helper_name, helper)):
        path = tmp_path / (module + ".py")
        path.write_text(body)
        inputs.append(PythonSource(module, body.encode(), str(path)))
    monkeypatch.syspath_prepend(str(tmp_path))
    sources = PythonSourceCollection(tuple(inputs))
    model = compile_data_operations(python_sources=sources)
    factory = resolve_prepared_factory(model, sources, model.operations[0].semantic_id)
    original = factory(identity="admitted-identity")
    assert original.identity == "admitted-identity"
    assert type(original).__module__ == helper_name
    copied = SimpleNamespace(identity=original.identity, plan_python=lambda **_: iter(()))
    monkeypatch.setattr(
        importlib.import_module(helper_name), "resolve_port", lambda identity: copied
    )
    with pytest.raises(PortRefusal, match=r"outside acquired source|qualified owner"):
        factory(identity="admitted-identity")


def test_deferred_failure_fenced_owner_cannot_release_another_attempt():
    from datetime import UTC, datetime

    from corpus_structure.orchestrate.data_operations import (
        NativeDemandExecutor,
        NativeRequestClaim,
    )
    from corpus_structure.semantic.claim_lifetime import ClaimFenceLost

    class ForbiddenEngine:
        def begin(self):
            raise AssertionError("a lost fence cannot perform native release")

    claim = NativeRequestClaim(
        "request:one", 1, 1, 1, "old-holder", "release:one", datetime.now(UTC)
    )

    class LostOwner:
        def check_claim(self, value):
            raise ClaimFenceLost(value, "replaced")

        def settle(self, *args):
            raise AssertionError("a lost fence cannot settle deferred work")

    executor = object.__new__(NativeDemandExecutor)
    executor.engine = ForbiddenEngine()
    executor._known_failure(
        claim, LostOwner(), RuntimeError("original failure"), phase="computation"
    )


def test_hydrated_consumer_preserves_typed_decimal_body_independently_of_json_display():
    from decimal import Decimal

    from corpus_structure.semantic.data_operation_consumers import SelectedConsumerValue
    from corpus_structure.semantic.data_operation_model import BoundRoleMember

    member = BoundRoleMember(
        "product:one", "kind:decimal", "subject:one", "original:one", b"{}", b"{}", (), b"{}"
    )
    value = SelectedConsumerValue(
        member, b'"0.1234567890123456789"', b'["decimal","0.1234567890123456789"]'
    )
    assert value.value() == Decimal("0.1234567890123456789")
    assert type(value.value()) is Decimal


def test_uncertain_thread_without_future_cannot_claim_physical_retirement():
    from types import SimpleNamespace

    from corpus_structure.orchestrate.data_operations import _RequestExecution
    from corpus_structure.semantic.cpu_execution import OwnedByteBudget

    class UnknownSubmit:
        def submit(self, callback):
            raise RuntimeError("no acknowledged future")

    budget = OwnedByteBudget(32)
    reservation = budget.admit(32)
    invocation = SimpleNamespace(
        pool=UnknownSubmit(),
        uncertain_python=[],
        physical_retired=False,
        cpu=SimpleNamespace(reservation_retired=lambda _: True),
        native_hosts=None,
        executor=SimpleNamespace(engine=None),
    )
    physical = _RequestExecution(invocation, reservation)
    with pytest.raises(RuntimeError, match="no acknowledged future"):
        physical.submit_python(lambda: None)
    assert physical.retired() is False
    reservation.release()
    assert budget.used_bytes == 32
    invocation.physical_retired = True
    assert physical.retired() is True
    invocation.uncertain_python[0][1].release()
    assert budget.used_bytes == 0
