"""Host lifetime, verified-basis cache custody and resource reuse controls."""

from collections import namedtuple
from types import SimpleNamespace

import pytest
from orchestrate.test_data_operation_byte_admission import prepared as prepared

from corpus_structure.core.execution_policy import CharacterizationExecutionPolicy
from corpus_structure.orchestrate.execution_host import ProcessExecutionHost, execution_host_scope
from corpus_structure.semantic.refusals import SemanticRefusal


def test_process_scope_shares_one_owner_and_rejects_concurrent_runs():
    with execution_host_scope() as host:
        with execution_host_scope() as nested:
            assert nested is host
            with host.run(CharacterizationExecutionPolicy()):
                with pytest.raises(RuntimeError, match="active run"):
                    with nested.run(CharacterizationExecutionPolicy()):
                        pytest.fail("a second run entered")
        assert not host._closed
    assert host._closed


def controlled_archive(monkeypatch):
    from corpus_structure.semantic import archive_reader, cpu_execution, data_operation_service, determinants

    Header = namedtuple("Header", "release_id profile content_digest finalized_digest marker")
    state = SimpleNamespace(marker="original", runtime_marker="original", acquisitions=[])
    monkeypatch.setattr(archive_reader, "_archive_header", lambda _, release: Header(
        release, "test", release, release, state.marker
    ))
    monkeypatch.setattr(determinants, "determinant_version", lambda _: "selected")

    def acquire(_connection, release, runtime, *, source_root):
        state.acquisitions.append((release, runtime, source_root))
        return SimpleNamespace(prepared=SimpleNamespace(release_id=release))

    monkeypatch.setattr(data_operation_service, "acquire_data_execution_basis", acquire)
    monkeypatch.setattr(cpu_execution, "release_capsule", lambda prepared: prepared.release_id.encode())
    connection = SimpleNamespace(execute=lambda _: SimpleNamespace(one=lambda: (state.runtime_marker,)))
    return state, connection


def test_verified_basis_reuses_only_exact_engine_header_runtime_and_root(monkeypatch, tmp_path):
    state, connection = controlled_archive(monkeypatch)
    first_engine, second_engine = object(), object()
    host = ProcessExecutionHost()
    policy = CharacterizationExecutionPolicy()
    try:
        with host.run(policy) as token:
            first = host.acquire_basis(first_engine, connection, "release:first", "runtime", source_root=tmp_path, token=token)
            assert host._borrowed[0].references == 1
        assert host.budget.used_bytes == len(b"release:first")
        with host.run(policy) as token:
            assert host.acquire_basis(first_engine, connection, "release:first", "runtime", source_root=tmp_path, token=token) is first
        assert len(state.acquisitions) == 1
        with host.run(policy) as token:
            host.acquire_basis(second_engine, connection, "release:first", "runtime", source_root=tmp_path, token=token)
        assert len(state.acquisitions) == 2
        state.marker = "administratively changed"
        with host.run(policy) as token:
            with pytest.raises(SemanticRefusal, match="archive/runtime changed"):
                host.acquire_basis(first_engine, connection, "release:first", "runtime", source_root=tmp_path, token=token)
    finally:
        host.close()
    assert host.budget.used_bytes == 0


def test_runtime_rewrite_refuses_and_idle_lru_releases_real_credit(monkeypatch):
    state, connection = controlled_archive(monkeypatch)
    engine = object()
    host = ProcessExecutionHost()
    policy = CharacterizationExecutionPolicy(max_idle_capsules=1)
    try:
        for release in ("old", "new"):
            with host.run(policy) as token:
                host.acquire_basis(engine, connection, release, "runtime", source_root=None, token=token)
        assert [key[1] for key in host._bases] == ["new"]
        assert host.budget.used_bytes == len(b"new")
        state.runtime_marker = "rewritten"
        with host.run(policy) as token:
            with pytest.raises(SemanticRefusal, match="archive/runtime changed"):
                host.acquire_basis(engine, connection, "new", "runtime", source_root=None, token=token)
    finally:
        host.close()


def test_two_runs_reuse_worker_and_capsule_with_actual_spawned_calls(monkeypatch, tmp_path, prepared):
    import importlib
    import inspect
    import json
    from dataclasses import replace

    from orchestrate.test_data_operation_byte_admission import Active, controlled_executor, policy_for

    from corpus_structure.semantic.data_operation_cpu import PythonCPUDescriptor, plan_cpu_call

    source = """from corpus_structure.semantic.types import PreparedRelease

def derive(value: int, prepared: PreparedRelease) -> int:
    prepared.validate_json('Thing', '{"id":"A"}')
    return value + 1
"""
    module = "process_host_reuse_kernel"
    path = tmp_path / (module + ".py")
    path.write_text(source)
    monkeypatch.syspath_prepend(str(tmp_path))
    function = importlib.import_module(module).derive
    signature = inspect.signature(function)
    descriptor = PythonCPUDescriptor(
        ((module, str(path), source.encode()),), module + ".derive", (),
        verification="prepared-kernel", prepared_parameter="prepared",
        prepared_release_id=prepared.release_id,
    )
    pids = []

    def scalar(value, *, execution_owner, check_active, **_):
        reply = yield from plan_cpu_call(
            descriptor, signature.bind(value, prepared), signature, verify=lambda: None,
            execution_owner=execution_owner, check_active=check_active,
        )
        pids.append(reply.pid)
        return json.loads(reply.content)

    executor, observed = controlled_executor(
        monkeypatch, prepared, replace(policy_for(prepared), workers=1, max_submissions=1),
        ("prepared",),
        {"prepared": SimpleNamespace(native_selections=(), requires_prepared_schema=True, plan_python=scalar)},
    )
    host = ProcessExecutionHost()
    generations, capsule_names, baselines = [], [], []
    try:
        for _ in range(2):
            with host.run(executor.policy) as token:
                with host.execution(executor, token) as physical:
                    executor._physical = physical
                    physical.select_operations(("prepared",))
                    generations.append(physical.cpu)
                    capsule_names.append(physical.cpu._release_capsules[prepared.release_id].reference.name)
                    baselines.append(host.budget.used_bytes)
                    receipts, _, _, failures = executor._drive_sweep(({},), b"{}", Active())
                    assert receipts == (b"0",) and not failures
        assert generations[0] is generations[1]
        assert len(pids) == 2 and pids[0] == pids[1]
        assert capsule_names[0] == capsule_names[1]
        assert baselines[0] == baselines[1] > 0
    finally:
        host.close()
    assert host.budget.used_bytes == 0 and not observed.live


def test_idle_cpu_generation_can_retire_inside_same_logical_run(monkeypatch, prepared):
    from orchestrate.test_data_operation_byte_admission import controlled_executor, policy_for

    from corpus_structure.orchestrate.execution_host import ExecutionPreparationDeferred

    _, connection = controlled_archive(monkeypatch)
    engine = object()
    executor, _ = controlled_executor(
        monkeypatch, prepared, policy_for(prepared), (), {},
    )
    host = ProcessExecutionHost()
    try:
        with host.run(executor.policy) as token:
            host.acquire_basis(engine, connection, "old", "runtime", source_root=None, token=token)
        old_key = next(iter(host._bases))
        with host.run(executor.policy) as token:
            with host.execution(executor, token) as physical:
                previous_cpu = physical.cpu
                request = SimpleNamespace(running=True, retired=lambda: True)
                physical.requests.append(request)
                with pytest.raises(ExecutionPreparationDeferred):
                    host._evict(old_key)
                assert old_key in host._bases and physical.cpu is previous_cpu
                request.running = False
                host._evict(old_key)
                assert old_key not in host._bases
                assert previous_cpu._physical_retired
                assert physical.cpu is host.resources.cpu and physical.cpu is not previous_cpu
    finally:
        host.close()
    assert host.budget.used_bytes == 0


def test_unconfirmed_join_quarantines_host_without_releasing_owned_credit():
    from corpus_structure.core.work import PhysicalRetirementUncertain

    host = ProcessExecutionHost()
    with host.run(CharacterizationExecutionPolicy()):
        reservation = host.budget.admit(100)
        failure = PhysicalRetirementUncertain("controlled group join is unconfirmed")

        def unconfirmed():
            raise failure

        host.resources = SimpleNamespace(
            providers=SimpleNamespace(close=lambda: None, retire=lambda: True),
            native_hosts=SimpleNamespace(close=lambda: None, physical_drained=True),
            cpu=SimpleNamespace(close=unconfirmed, _physical_retired=False),
            pool=SimpleNamespace(close=lambda: None, drained=True),
        )
        with pytest.raises(BaseExceptionGroup):
            host.retire_resources()
        assert host.budget.used_bytes == 100
        with pytest.raises(PhysicalRetirementUncertain, match="managed process cleanup"):
            host._check()
        # This control has no native child. Remove its injected failed owner so
        # test teardown does not pretend to join or reset a real generation.
        host.resources = None
        reservation.release()
        host._quarantine = None
    host.close()
