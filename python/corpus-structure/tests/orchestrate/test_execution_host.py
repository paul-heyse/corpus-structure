"""Host lifetime, verified-basis cache custody and resource reuse controls."""

from collections import namedtuple
from types import SimpleNamespace

import pytest
from orchestrate.executor_support import prepared as prepared

from corpus_structure.core.execution_policy import CharacterizationExecutionPolicy
from corpus_structure.orchestrate.execution_host import ProcessExecutionHost, execution_host_scope
from corpus_structure.semantic.refusals import SemanticRefusal


def test_process_scope_shares_one_owner_and_rejects_concurrent_runs():
    with execution_host_scope() as host:
        with execution_host_scope() as nested:
            assert nested is host
            with (
                host.run(CharacterizationExecutionPolicy()),
                pytest.raises(RuntimeError, match="active run"),
                nested.run(CharacterizationExecutionPolicy()),
            ):
                pytest.fail("a second run entered")
        assert not host._closed
    assert host._closed


def controlled_archive(monkeypatch):
    from corpus_structure.semantic import (
        archive_reader,
        cpu_execution,
        data_operation_service,
        determinants,
    )

    Header = namedtuple("Header", "release_id profile content_digest finalized_digest marker")
    state = SimpleNamespace(
        marker="original",
        runtime_marker="original",
        acquisitions=[],
        runtime_manifest=b"runtime-manifest",
        runtime_archive=b"runtime-archive",
    )
    monkeypatch.setattr(
        archive_reader,
        "_archive_header",
        lambda _, release: Header(release, "test", release, release, state.marker),
    )
    monkeypatch.setattr(determinants, "determinant_version", lambda _: "selected")

    def acquire(_connection, release, runtime, *, source_root):
        state.acquisitions.append((release, runtime, source_root))
        return SimpleNamespace(
            prepared=SimpleNamespace(release_id=release),
            runtime=SimpleNamespace(manifest=state.runtime_manifest, archive=state.runtime_archive),
        )

    monkeypatch.setattr(data_operation_service, "acquire_data_execution_basis", acquire)
    monkeypatch.setattr(
        cpu_execution, "release_capsule", lambda prepared: prepared.release_id.encode()
    )
    connection = SimpleNamespace(
        execute=lambda _: SimpleNamespace(one=lambda: (state.runtime_marker,))
    )
    return state, connection


def test_verified_basis_reuses_only_exact_engine_header_runtime_and_root(monkeypatch, tmp_path):
    state, connection = controlled_archive(monkeypatch)
    first_engine, second_engine = object(), object()
    host = ProcessExecutionHost()
    policy = CharacterizationExecutionPolicy()
    try:
        with host.run(policy) as token:
            first = host.acquire_basis(
                first_engine,
                connection,
                "release:first",
                "runtime",
                source_root=tmp_path,
                token=token,
            )
            assert host._borrowed[0].references == 1
        assert host.budget.used_bytes == len(b"release:first") + len(state.runtime_manifest) + len(
            state.runtime_archive
        )
        with host.run(policy) as token:
            assert (
                host.acquire_basis(
                    first_engine,
                    connection,
                    "release:first",
                    "runtime",
                    source_root=tmp_path,
                    token=token,
                )
                is first
            )
        assert len(state.acquisitions) == 1
        with host.run(policy) as token:
            host.acquire_basis(
                second_engine,
                connection,
                "release:first",
                "runtime",
                source_root=tmp_path,
                token=token,
            )
        assert len(state.acquisitions) == 2
        state.marker = "administratively changed"
        with (
            host.run(policy) as token,
            pytest.raises(SemanticRefusal, match="archive/runtime changed"),
        ):
            host.acquire_basis(
                first_engine,
                connection,
                "release:first",
                "runtime",
                source_root=tmp_path,
                token=token,
            )
    finally:
        host.close()
    assert host.budget.used_bytes == 0


@pytest.mark.parametrize("determinant", ["root", "library", "compiler"])
def test_execution_basis_invalidates_on_changed_preparation_basis(
    monkeypatch, tmp_path, determinant
):
    from corpus_structure.semantic import determinants, types

    state, connection = controlled_archive(monkeypatch)
    engine = object()
    host = ProcessExecutionHost()
    policy = CharacterizationExecutionPolicy()
    try:
        with host.run(policy) as token:
            first = host.acquire_basis(
                engine,
                connection,
                "release:first",
                "runtime",
                source_root=tmp_path,
                token=token,
            )
        root = tmp_path
        if determinant == "root":
            root = tmp_path / "other-root"
        elif determinant == "library":
            version = determinants.determinant_version
            monkeypatch.setattr(
                determinants,
                "determinant_version",
                lambda name: "independent-version" if name == "psycopg" else version(name),
            )
        else:
            monkeypatch.setattr(types, "SEMANTIC_COMPILER_VERSION", "independent-version")
        with host.run(policy) as token:
            other = host.acquire_basis(
                engine,
                connection,
                "release:first",
                "runtime",
                source_root=root,
                token=token,
            )
        assert other is not first
        assert len(state.acquisitions) == 2
    finally:
        host.close()


def test_runtime_rewrite_refuses_and_idle_lru_releases_real_credit(monkeypatch):
    state, connection = controlled_archive(monkeypatch)
    engine = object()
    host = ProcessExecutionHost()
    policy = CharacterizationExecutionPolicy(max_idle_capsules=1)
    try:
        for release in ("old", "new"):
            with host.run(policy) as token:
                host.acquire_basis(
                    engine, connection, release, "runtime", source_root=None, token=token
                )
        assert [key[1] for key in host._bases] == ["new"]
        assert host.budget.used_bytes == len(b"new") + len(state.runtime_manifest) + len(
            state.runtime_archive
        )
        state.runtime_marker = "rewritten"
        with (
            host.run(policy) as token,
            pytest.raises(SemanticRefusal, match="archive/runtime changed"),
        ):
            host.acquire_basis(engine, connection, "new", "runtime", source_root=None, token=token)
    finally:
        host.close()


def test_two_runs_reuse_worker_and_capsule_with_actual_spawned_calls(
    monkeypatch, tmp_path, prepared
):
    import importlib
    import inspect
    import json
    from dataclasses import replace

    from orchestrate.executor_support import (
        execution_case,
        policy_for,
    )

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
        ((module, str(path), source.encode()),),
        module + ".derive",
        (),
        verification="prepared-kernel",
        prepared_parameter="prepared",
        prepared_release_id=prepared.release_id,
    )
    pids, generations, capsule_names, baselines = [], [], [], []

    def scalar(value, *, execution_owner, check_active, **_):
        generations.append(execution_owner.cpu.scope)
        capsule_names.append(execution_owner.cpu.capsule.name)
        baselines.append(execution_owner.invocation.host.budget.used_bytes)
        reply = yield from plan_cpu_call(
            descriptor,
            signature.bind(value, prepared),
            signature,
            verify=lambda: None,
            execution_owner=execution_owner,
            check_active=check_active,
        )
        pids.append(reply.pid)
        return json.loads(reply.content)

    host = ProcessExecutionHost()
    policy = replace(policy_for(prepared), workers=1, max_submissions=1)
    observed_runs = []
    try:
        for _ in range(2):
            with host.run(policy) as token:
                executor, observed = execution_case(
                    monkeypatch,
                    prepared,
                    policy,
                    ("prepared",),
                    {
                        "prepared": SimpleNamespace(
                            native_selections=(),
                            requires_prepared_schema=True,
                            plan_python=scalar,
                        )
                    },
                    execution_host=host,
                    host_run=token,
                )
                result = executor.advance("controlled-demand")
                assert [json.loads(receipt)["receipt_id"] for receipt in result.receipts] == ["0"]
                observed_runs.append(observed)
        assert generations[0] is generations[1]
        assert len(pids) == 2 and pids[0] == pids[1]
        assert capsule_names[0] == capsule_names[1]
        assert baselines[0] == baselines[1] > 0
    finally:
        host.close()
    assert host.budget.used_bytes == 0 and all(not observed.live for observed in observed_runs)


def test_idle_cpu_generation_can_retire_inside_same_logical_run(monkeypatch, prepared):
    from orchestrate.executor_support import execution_case, policy_for

    from corpus_structure.orchestrate.execution_host import ExecutionPreparationDeferred

    _, connection = controlled_archive(monkeypatch)
    engine = object()
    executor, _ = execution_case(
        monkeypatch,
        prepared,
        policy_for(prepared),
        (),
        {},
    )
    host = ProcessExecutionHost()
    try:
        with host.run(executor.policy) as token:
            host.acquire_basis(engine, connection, "old", "runtime", source_root=None, token=token)
        old_key = next(iter(host._bases))
        with host.run(executor.policy) as token, host.execution(executor, token) as physical:
            previous_cpu = physical.cpu
            credit = host.budget.admit(executor.reservation)
            physical.pending_reservations.add(credit)
            try:
                assert not physical.requests
                with pytest.raises(ExecutionPreparationDeferred):
                    host._evict(old_key)
                assert old_key in host._bases and physical.cpu is previous_cpu
            finally:
                physical.pending_reservations.remove(credit)
                credit.release()
            request = SimpleNamespace(running=True, retired=lambda: True)
            request.release_retired_inputs = lambda: not request.running and request.retired()
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


def test_large_runtime_bodies_participate_in_idle_limit_and_total_admission(monkeypatch):
    from corpus_structure.semantic.cpu_execution import CapacityExceeded

    state, connection = controlled_archive(monkeypatch)
    state.runtime_manifest = b"m" * 1000
    state.runtime_archive = b"a" * 9000
    host = ProcessExecutionHost()
    policy = CharacterizationExecutionPolicy(max_idle_capsule_bytes=100)
    try:
        with host.run(policy) as token:
            host.acquire_basis(
                object(), connection, "tiny", "runtime", source_root=None, token=token
            )
            assert host.budget.used_bytes == 10004
        assert not host._bases and host.budget.used_bytes == 0
        small = CharacterizationExecutionPolicy(
            max_owned_bytes=100,
            max_packet_bytes=1,
            max_reply_bytes=1,
            max_native_request_bytes=1,
            max_native_reply_bytes=1,
        )
        with host.run(small) as token:
            with pytest.raises(CapacityExceeded, match="one complete request"):
                host.acquire_basis(
                    object(), connection, "tiny", "runtime", source_root=None, token=token
                )
            assert not host._bases and host.budget.used_bytes == 0
    finally:
        host.close()


def test_shared_immutable_runtime_buffers_are_charged_once_until_last_basis_eviction(monkeypatch):
    state, connection = controlled_archive(monkeypatch)
    shared = b"one actual retained buffer" * 100
    state.runtime_manifest = state.runtime_archive = shared
    host = ProcessExecutionHost()
    try:
        for engine in (object(), object()):
            with host.run(CharacterizationExecutionPolicy()) as token:
                host.acquire_basis(
                    engine, connection, "tiny", "runtime", source_root=None, token=token
                )
        # The two independently encoded capsules are separate owned buffers;
        # both runtime fields and both cached bases share exactly one byte object.
        assert host.budget.used_bytes == len(shared) + 2 * len(b"tiny")
        first = next(iter(host._bases))
        host._evict(first)
        assert host.budget.used_bytes == len(shared) + len(b"tiny")
    finally:
        host.close()
    assert not host._bodies and host.budget.used_bytes == 0


def test_unstarted_stage_a_credit_defers_preparation_without_evicting_cpu(prepared, monkeypatch):
    from orchestrate.executor_support import execution_case, policy_for

    from corpus_structure.orchestrate.execution_host import ExecutionPreparationDeferred
    from corpus_structure.semantic.cpu_execution import release_capsule

    executor, _ = execution_case(
        monkeypatch,
        prepared,
        policy_for(prepared),
        (),
        {"prepared": SimpleNamespace(native_selections=(), requires_prepared_schema=True)},
    )
    host = ProcessExecutionHost()
    try:
        with host.run(executor.policy) as token, host.execution(executor, token) as physical:
            executor._physical = physical
            physical.select_operations(("prepared",))
            generation = physical.cpu
            capsule = generation._release_capsules[prepared.release_id]
            capsule_bytes = len(release_capsule(prepared))
            assert host.budget.used_bytes == capsule_bytes
            reservation = host.budget.admit(executor.reservation)
            physical.pending_reservations.add(reservation)
            try:
                assert not physical.requests  # The reserved child has not started.
                assert physical.has_live_requests()
                assert host.budget.limit - host.budget.used_bytes < executor.reservation
                host.ensure_request_room(executor.reservation)
                with pytest.raises(ExecutionPreparationDeferred):
                    host.cpu_for_release(prepared, executor.reservation)
                with pytest.raises(ExecutionPreparationDeferred):
                    host.retire_cpu()
                assert physical.cpu is generation and not generation._physical_retired
                assert generation._release_capsules[prepared.release_id] is capsule
                assert host.budget.used_bytes == capsule_bytes + executor.reservation
            finally:
                physical.pending_reservations.remove(reservation)
                reservation.release()
            # Abandoning that unstarted child makes preparation possible
            # under exactly the same policy, generation and retained capsule.
            view = host.cpu_for_release(prepared, executor.reservation)
            assert view.scope is generation and view.capsule is capsule.reference
            assert host.budget.used_bytes == capsule_bytes <= host.budget.limit
    finally:
        host.close()
    assert host.budget.used_bytes == 0
