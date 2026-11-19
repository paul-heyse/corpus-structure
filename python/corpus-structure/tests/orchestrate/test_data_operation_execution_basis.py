"""Independent controls for immutable request-generation execution custody."""

import importlib
import inspect
import json
from contextlib import nullcontext
from dataclasses import replace
from types import SimpleNamespace
from typing import Any, cast

import pytest
from orchestrate.executor_support import (
    Active,
    execution_case,
    executor_case,
    policy_for,
)
from orchestrate.executor_support import (
    prepared as prepared,
)

from corpus_structure.orchestrate import data_operations
from corpus_structure.semantic.cpu_execution import CPUExecutionScope, release_capsule
from corpus_structure.semantic.data_operation_cpu import PythonCPUDescriptor
from corpus_structure.semantic.identity import canonical_bytes


def attached_basis():
    return dict(
        request_id="request:original",
        generation=5,
        release_id="release:original",
        runtime_id="runtime:original",
        binding={"read_id": "read:original"},
        binding_demand_id="demand:original",
        binding_obligation_id="obligation:original",
        action="compute",
        retained_intent_id=None,
    )


@pytest.mark.parametrize("state", ["claimed", "no-work"])
def test_claim_uses_authenticated_expected_generation_and_original_basis(
    monkeypatch, state, prepared
):
    metadata = attached_basis()
    seen, claims = [], []
    executor = executor_case()
    executor.holder = "owner"
    from corpus_structure.semantic.data_operation_runtime import RuntimeBinding

    executor.prepared = prepared
    executor.runtime = RuntimeBinding(prepared.release_id, "runtime:target", b"", b"")

    def claim(payload):
        seen.append(payload)
        return (
            {"items": [{"state": "no-work"}]}
            if state == "no-work"
            else {
                "items": [
                    {
                        "state": "claimed",
                        "result": dict(
                            metadata,
                            state="claimed",
                            task_id=13,
                            attempt=2,
                            holder="owner",
                            lease_until="2026-11-17T00:00:00Z",
                            trust_snapshot={},
                        ),
                    }
                ]
            }
        )

    cast(Any, executor.native_io).calls = SimpleNamespace(claim_data_requests=claim)
    result, _ = executor._claim(
        SimpleNamespace(native=canonical_bytes(metadata)), SimpleNamespace(add_claim=claims.append)
    )
    assert seen == [
        dict(
            items=[dict(request_id="request:original", generation=5)],
            holder="owner",
            lease_seconds=300,
        )
    ]
    if state == "claimed":
        assert result is claims[0]
        assert (result.release_id, result.runtime_id, result.generation) == (
            "release:original",
            "runtime:original",
            5,
        )
    else:
        assert result is None and not claims


def test_reconstructed_binding_consumes_original_pinned_read_without_attachment(monkeypatch):
    metadata = attached_basis()
    seen: list[tuple[object, ...]] = []
    executor = executor_case()
    context = SimpleNamespace(model=object())
    snapshot = dict(
        read_id="read:original",
        demand_id="demand:original",
        obligations=[dict(obligation_id="obligation:original")],
        selection=dict(operations=[dict(operation="operation:original")]),
    )
    bound = SimpleNamespace(
        request_id="request:original",
        binding=canonical_bytes(metadata["binding"]),
        operation="operation:original",
        subject="subject:original",
        request=b"request",
        admission=b"admission",
        resolved=object(),
        binding_result=object(),
    )

    def read(request):
        seen.append(("read", request))
        return snapshot

    def bindings(value, **options):
        seen.append(("binding", value["read_id"], options))
        return (bound,)

    storage = SimpleNamespace(read_demand_result=read)
    cast(Any, executor.native_io).calls = storage
    cast(Any, executor.native_io).plan = lambda _model: SimpleNamespace(bound_requests=bindings)
    monkeypatch.setattr(
        data_operations, "ReadyDataRequest", lambda **values: SimpleNamespace(**values)
    )
    target = SimpleNamespace(obligation="obligation:target", native=b"native-target")
    original, operations = executor._generation_ready(
        target, "request:original", metadata, context, b"current-authorization"
    )
    assert seen == [
        (
            "read",
            dict(
                demand_id="demand:original",
                read_id="read:original",
                limit=1,
                obligation_id="obligation:original",
            ),
        ),
        ("binding", "read:original", dict(authorization=b"current-authorization", retained=True)),
    ]
    assert original.binding == canonical_bytes(metadata["binding"])
    assert original.obligation == "obligation:target"
    assert operations == ("operation:original",)
    bound.binding = canonical_bytes({"read_id": "read:latest"})
    with pytest.raises(ValueError, match="original frozen binding"):
        executor._generation_ready(
            target, "request:original", metadata, context, b"current-authorization"
        )


def test_batches_never_mix_distinct_execution_bases(monkeypatch, prepared):
    batches = []

    def batch(members, **_):
        batches.append(tuple(member.values for member in members))
        if False:
            yield
        return SimpleNamespace(members=tuple((member.member, member.values) for member in members))

    port = SimpleNamespace(native_selections=(), plan_batch_python=batch)
    executor, observed = execution_case(
        monkeypatch, prepared, policy_for(prepared, credits=4), ("batch",) * 4, {"batch": port}
    )
    contexts = [
        SimpleNamespace(
            model=executor.model,
            basis=SimpleNamespace(
                key=("release:" + name, "runtime:" + name),
                prepared=prepared,
                runtime=SimpleNamespace(runtime_id="runtime:" + name),
                sources=executor.sources,
                prepared_sources=executor.sources,
            ),
            cpu=None,
            ports={},
            consumer_selectors={},
            prepared_schema=False,
            admitted_operations=set(),
        )
        for name in ("old", "new")
    ]
    executor._ready_items = tuple(
        replace(
            item,
            native=canonical_bytes(
                {
                    **json.loads(item.native),
                    "release_id": contexts[int(item.obligation) % 2].basis.key[0],
                    "runtime_id": contexts[int(item.obligation) % 2].basis.key[1],
                }
            ),
        )
        for item in executor._ready_items
    )
    executor._ready_context = lambda item: contexts[int(item.obligation) % 2]
    executor._execution_context = lambda claim: contexts[int(claim.request_id) % 2]

    result = executor.advance("controlled-demand")
    assert result.receipt_count == 4
    assert sorted(batches) == [(0, 2), (1, 3)]
    assert executor.budget.used_bytes == 0 and not observed.live


def test_two_exact_release_capsules_share_one_cpu_pool(tmp_path, monkeypatch, prepared):
    from corpus_structure.semantic.prepare import prepare_release
    from corpus_structure.semantic.types import SourceArtifact, SourceBundle

    other = prepare_release(
        SourceBundle(
            "other",
            (
                SourceArtifact(
                    "other",
                    b"""id: urn:other
name: other
prefixes: {o: 'urn:other:'}
default_prefix: o
classes: {Other: {}}
""",
                ),
            ),
        )
    )
    path = tmp_path / "basis_kernel.py"
    path.write_text(
        "from corpus_structure.semantic.types import PreparedRelease\n\ndef release(prepared: PreparedRelease) -> str:\n    return prepared.release_id\n"
    )
    monkeypatch.syspath_prepend(str(tmp_path))
    function = importlib.import_module("basis_kernel").release
    signature = inspect.signature(function)
    from dataclasses import replace

    scope = CPUExecutionScope(
        prepared, replace(policy_for(prepared, credits=4), workers=1), retain_schema=False
    )
    try:
        views = [scope.for_release(value) for value in (prepared, other)]
        assert scope.preparation_bytes == len(release_capsule(prepared)) + len(
            release_capsule(other)
        )
        import pickle

        names = [view.capsule.name for view in views]
        assert all(len(pickle.dumps(view.capsule)) < 1024 for view in views)
        pools = []
        for view, value in zip(views, (prepared, other), strict=True):
            descriptor = PythonCPUDescriptor(
                (("basis_kernel", str(path), path.read_bytes()),),
                "basis_kernel.release",
                (),
                verification="prepared-kernel",
                prepared_parameter="prepared",
                prepared_release_id=value.release_id,
            )
            admission = view.try_admit()
            assert admission is not None
            handle = view.submit_closed_python(
                admission,
                descriptor.packet(signature.bind(value).arguments, signature),
                lambda: None,
            )
            handle.future.result(timeout=30)
            reply = handle.collect()
            assert json.loads(reply.content) == value.release_id
            pools.append(scope._pool)
            assert handle.retire()
        assert pools[0] is pools[1] and pools[0] is not None
    finally:
        scope.close()
    assert scope.budget.used_bytes == 0
    from multiprocessing.shared_memory import SharedMemory

    for name in names:
        with pytest.raises(FileNotFoundError):
            SharedMemory(name=name, track=False)


@pytest.mark.parametrize("phase", ["startup", "submit"])
def test_shared_capsule_stays_owned_through_unacknowledged_pool_failure(
    monkeypatch, prepared, phase
):
    from multiprocessing.shared_memory import SharedMemory

    from corpus_structure.semantic import cpu_execution

    scope = CPUExecutionScope(prepared, policy_for(prepared, credits=4), retain_schema=False)
    view = scope.for_release(prepared)
    name = view.capsule.name
    retained = scope.preparation_bytes

    def fail(*args, **kwargs):
        raise RuntimeError("controlled unacknowledged " + phase)

    try:
        if phase == "startup":
            monkeypatch.setattr(cpu_execution, "ProcessPoolExecutor", fail)
            with pytest.raises(RuntimeError, match="unacknowledged startup"):
                scope.prepare()
        else:
            scope.prepare()
            assert scope._pool is not None
            monkeypatch.setattr(scope._pool, "submit", fail)
            admission = view.try_admit()
            assert admission is not None
            with pytest.raises(RuntimeError, match="unacknowledged submit"):
                view.submit_closed_python(admission, b"no acknowledged child", lambda: None)
        assert scope.budget.used_bytes >= retained > 0
        memory = SharedMemory(name=name, track=False)
        memory.close()
    finally:
        scope.close()
    assert scope.budget.used_bytes == 0
    with pytest.raises(FileNotFoundError):
        SharedMemory(name=name, track=False)


def test_shared_capsule_descriptor_rejects_changed_archive_digest(prepared):
    from dataclasses import replace

    scope = CPUExecutionScope(
        prepared, replace(policy_for(prepared, credits=4), workers=1), retain_schema=False
    )
    view = scope.for_release(prepared)
    try:
        # The valid descriptor loads its release before the deliberately invalid
        # call body fails. The next request must not trust a changed descriptor.
        first = scope.try_admit()
        assert first is not None
        primed = view.submit_closed_python(first, b"{}", lambda: None)
        original_reply = primed.future.result(timeout=30)
        with pytest.raises(ValueError):
            primed.collect()
        assert primed.retire()
        admission = scope.try_admit()
        assert admission is not None
        handle = scope._submit(
            admission,
            b"{}",
            lambda: None,
            "closed-python",
            capsule=replace(view.capsule, digest="0" * 64),
        )
        changed_reply = handle.future.result(timeout=30)
        assert changed_reply.pid == original_reply.pid
        with pytest.raises(ValueError, match="shared capsule bytes differ"):
            handle.collect()
        assert handle.retire()
        assert scope.budget.used_bytes == scope.preparation_bytes > 0
    finally:
        scope.close()
    assert scope.budget.used_bytes == 0


@pytest.mark.parametrize("refuse", [False, True])
def test_fresh_hydration_uses_its_own_transaction_after_claim_commit(monkeypatch, refuse, prepared):
    from contextlib import contextmanager

    from corpus_structure.semantic.data_operation_consumers import HydratedConsumerSelection

    events = []
    executor, _ = execution_case(
        monkeypatch,
        prepared,
        policy_for(prepared),
        ("scalar",),
        {"scalar": SimpleNamespace(native_selections=())},
    )
    unit = executor.native_io
    native_claim = unit.calls.replies["claim_data_requests"]

    def claim_reply(payload):
        events.append("claim")
        return native_claim(payload)

    unit.calls.replies["claim_data_requests"] = claim_reply

    @contextmanager
    def transaction():
        events.append("begin claim")
        yield unit
        events.append("commit claim")

    def hydrate(model, selected, **options):
        events.append("hydrate")
        assert selected.subject == "0"
        if refuse:
            raise ValueError("controlled hydration refusal")
        return HydratedConsumerSelection(selected, (), measured_bytes=10)

    unit.transaction, unit.hydrate_inputs = transaction, hydrate
    physical = SimpleNamespace(
        hydrated_inputs=None,
        hydrated_sizes={},
        consumer_inputs={},
        consumer_results={},
        binding_rows={},
    )
    ready = executor._ready_items[0]
    claim, result = executor._claim(
        ready,
        SimpleNamespace(add_claim=lambda _: events.append("renew committed claim")),
    )
    assert claim is not None and result["request_id"] == "0"
    assert events == ["begin claim", "claim", "commit claim", "renew committed claim"]
    if refuse:
        with pytest.raises(ValueError, match="controlled hydration refusal"):
            executor._hydrate(ready, physical, context=executor._execution_context(claim))
        assert events[-2:] == ["begin claim", "hydrate"]
        assert physical.hydrated_sizes == {}
    else:
        assert executor._hydrate(ready, physical, context=executor._execution_context(claim)) == ()
        assert events[-3:] == ["begin claim", "hydrate", "commit claim"]
        assert physical.hydrated_sizes == {"0": 10}


def test_claim_set_preserves_refusal_siblings_and_owns_repeated_identity_once(monkeypatch):
    metadata = attached_basis()
    events, owners = [], []
    executor = executor_case()
    executor.holder = "owner"
    native = dict(
        metadata,
        state="claimed",
        task_id=13,
        attempt=2,
        holder="owner",
        lease_until="2026-11-17T00:00:00Z",
        trust_snapshot={},
    )

    def claim_set(payload):
        events.append(payload)
        return {
            "items": [
                {"state": "refused", "sqlstate": "22023", "reason": "controlled refusal"},
                {"state": "claimed", "result": native},
                {"state": "claimed", "result": native},
                {"state": "no-work"},
            ]
        }

    cast(Any, executor.native_io).calls = SimpleNamespace(claim_data_requests=claim_set)
    items = tuple(SimpleNamespace(native=canonical_bytes(metadata)) for _ in range(4))
    result = executor._claim_many(items, SimpleNamespace(add_claim=owners.append))
    assert len(events) == 1 and len(events[0]["items"]) == 4
    assert result[0].claim is None and "controlled refusal" in str(result[0].error)
    assert result[1].claim is owners[0] and len(owners) == 1
    assert result[2].claim is None and result[2].error is None
    assert result[3].claim is None and result[3].error is None


def test_public_advance_uses_controlled_native_transactions_without_engine_access():
    from orchestrate.executor_support import ControlledNativeIO, executor_case

    native_io = ControlledNativeIO()
    executor = executor_case(native_io=native_io)
    snapshot = dict(
        demand_id="authored-demand",
        release_id=executor.prepared.release_id,
        runtime_id=executor.runtime.runtime_id,
        state="active",
        obligations=[],
        uses=[],
        populations=[],
        continuation=None,
        intent={"discovery": []},
        selection={"version": "data-demand-intent-v2", "operations": [{"operation": "scalar"}]},
    )
    reads = []

    def resume(demand, **options):
        reads.append(demand)
        return snapshot

    native_io.plan = lambda model: SimpleNamespace(
        ready=lambda *args, **options: (),
        resume=resume,
        logical_progress=0,
        selected_population_ids=(),
        refusals=(),
    )
    owner = Active()
    native_io.claims = lambda holder: nullcontext(owner)
    result = executor.advance("authored-demand")
    assert result.demand_id == "authored-demand"
    assert result.receipt_count == 0
    assert reads == ["authored-demand", "authored-demand"]
