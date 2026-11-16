"""Independent controls for immutable request-generation execution custody."""

import importlib
import inspect
import json
from contextlib import nullcontext
from types import SimpleNamespace

import pytest

from corpus_structure.orchestrate import data_operations
from corpus_structure.orchestrate.data_operations import NativeDemandExecutor
from corpus_structure.semantic.cpu_execution import CPUExecutionScope, release_capsule
from corpus_structure.semantic.data_operation_cpu import PythonCPUDescriptor
from corpus_structure.semantic.identity import canonical_bytes
from orchestrate.test_data_operation_byte_admission import (
    Active,
    controlled_executor,
    policy_for,
    prepared,
)


def attached_basis():
    return dict(
        request_id="request:original", generation=5, release_id="release:original",
        runtime_id="runtime:original", binding={"read_id": "read:original"},
        binding_demand_id="demand:original", binding_obligation_id="obligation:original",
        action="compute", retained_intent_id=None,
    )


@pytest.mark.parametrize("state", ["claimed", "no-work"])
def test_claim_uses_authenticated_expected_generation_and_original_basis(monkeypatch, state):
    metadata = attached_basis()
    seen, claims = [], []
    executor = object.__new__(NativeDemandExecutor)
    executor.engine = SimpleNamespace(begin=lambda: nullcontext(None))
    executor.holder = "owner"
    executor.prepared = SimpleNamespace(release_id="release:target")
    executor.runtime = SimpleNamespace(runtime_id="runtime:target")

    def claim(payload):
        seen.append(payload)
        return {"state": "no-work"} if state == "no-work" else dict(
            metadata, state="claimed", task_id=13, attempt=2, holder="owner",
            lease_until="2026-11-17T00:00:00Z", trust_snapshot={},
        )

    monkeypatch.setattr(data_operations, "DataOperationStorage", lambda _: SimpleNamespace(claim_data_request=claim))
    result, _ = executor._claim(SimpleNamespace(native=canonical_bytes(metadata)), SimpleNamespace(add_claim=claims.append))
    assert seen == [dict(request_id="request:original", generation=5, holder="owner", lease_seconds=300)]
    if state == "claimed":
        assert result is claims[0]
        assert (result.release_id, result.runtime_id, result.generation) == ("release:original", "runtime:original", 5)
    else:
        assert result is None and not claims


def test_reconstructed_binding_consumes_original_pinned_read_without_attachment(monkeypatch):
    metadata = attached_basis()
    seen = []
    executor = object.__new__(NativeDemandExecutor)
    executor.engine = SimpleNamespace(begin=lambda: nullcontext(None))
    context = SimpleNamespace(model=object())
    snapshot = dict(
        read_id="read:original", demand_id="demand:original",
        obligations=[dict(obligation_id="obligation:original")],
        selection=dict(operations=[dict(operation="operation:original")]),
    )
    bound = SimpleNamespace(
        request_id="request:original", binding=canonical_bytes(metadata["binding"]),
        operation="operation:original", subject="subject:original", request=b"request",
        admission=b"admission", resolved=object(), binding_result=object(),
    )

    def read(request):
        seen.append(("read", request))
        return snapshot

    def bindings(value, **options):
        seen.append(("binding", value["read_id"], options))
        return (bound,)

    storage = SimpleNamespace(read_demand_result=read)
    monkeypatch.setattr(data_operations, "DataOperationStorage", lambda _: storage)
    monkeypatch.setattr(data_operations, "DemandPlanner", lambda *_: SimpleNamespace(bound_requests=bindings))
    monkeypatch.setattr(data_operations, "ReadyDataRequest", lambda **values: SimpleNamespace(**values))
    target = SimpleNamespace(obligation="obligation:target", native=b"native-target")
    original, operations = executor._generation_ready(target, "request:original", metadata, context, b"current-authorization")
    assert seen == [
        ("read", dict(demand_id="demand:original", read_id="read:original", limit=1000)),
        ("binding", "read:original", dict(authorization=b"current-authorization", retained=True)),
    ]
    assert original.binding == canonical_bytes(metadata["binding"])
    assert original.obligation == "obligation:target"
    assert operations == ("operation:original",)
    bound.binding = canonical_bytes({"read_id": "read:latest"})
    with pytest.raises(ValueError, match="original frozen binding"):
        executor._generation_ready(target, "request:original", metadata, context, b"current-authorization")


def test_batches_never_mix_distinct_execution_bases(monkeypatch, prepared):
    batches = []

    def batch(members, **_):
        batches.append(tuple(member.values for member in members))
        if False:
            yield
        return SimpleNamespace(members=tuple((member.member, member.values) for member in members))

    port = SimpleNamespace(native_selections=(), plan_batch_python=batch)
    executor, observed = controlled_executor(monkeypatch, prepared, policy_for(prepared, credits=4), ("batch",) * 4, {"batch": port})
    contexts = [
        SimpleNamespace(model=executor.model, basis=SimpleNamespace(key=("release:" + name, "runtime:" + name)), cpu=None)
        for name in ("old", "new")
    ]
    executor._ready_context = lambda item: contexts[int(item.obligation) % 2]
    executor._execution_context = lambda claim: contexts[int(claim.request_id) % 2]
    from corpus_structure.orchestrate.data_operations import _InvocationExecution, _OwnedPythonPool

    with _OwnedPythonPool(2) as pool, _InvocationExecution(executor, pool) as physical:
        executor._physical = physical
        receipts, _, _, failures = executor._drive_page({}, b"{}", Active())
    assert len(receipts) == 4 and not failures
    assert sorted(batches) == [(0, 2), (1, 3)]
    assert executor.budget.used_bytes == 0 and not observed.live


def test_two_exact_release_capsules_share_one_cpu_pool(tmp_path, monkeypatch, prepared):
    from corpus_structure.semantic import SourceArtifact, SourceBundle, prepare_release

    other = prepare_release(SourceBundle("other", (SourceArtifact("other", b"""id: urn:other
name: other
prefixes: {o: 'urn:other:'}
default_prefix: o
classes: {Other: {}}
"""),)))
    path = tmp_path / "basis_kernel.py"
    path.write_text("from corpus_structure.semantic.types import PreparedRelease\n\ndef release(prepared: PreparedRelease) -> str:\n    return prepared.release_id\n")
    monkeypatch.syspath_prepend(str(tmp_path))
    function = importlib.import_module("basis_kernel").release
    signature = inspect.signature(function)
    scope = CPUExecutionScope(prepared, policy_for(prepared, credits=4), retain_schema=False)
    try:
        views = [scope.for_release(value) for value in (prepared, other)]
        assert scope.preparation_bytes == len(release_capsule(prepared)) + len(release_capsule(other))
        pools = []
        for view, value in zip(views, (prepared, other), strict=True):
            descriptor = PythonCPUDescriptor(
                (("basis_kernel", str(path), path.read_bytes()),), "basis_kernel.release", (),
                verification="prepared-kernel", prepared_parameter="prepared", prepared_release_id=value.release_id,
            )
            admission = view.try_admit()
            assert admission is not None
            handle = view.submit_closed_python(admission, descriptor.packet(signature.bind(value).arguments, signature), lambda: None)
            handle.future.result(timeout=30)
            reply = handle.collect()
            assert json.loads(reply.content) == value.release_id
            pools.append(scope._pool)
            assert handle.retire()
        assert pools[0] is pools[1] and pools[0] is not None
    finally:
        scope.close()
    assert scope.budget.used_bytes == 0
