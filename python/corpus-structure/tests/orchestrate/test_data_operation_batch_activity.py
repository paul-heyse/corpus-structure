"""Shared batches observe member ownership throughout physical execution."""

from datetime import UTC, datetime
from types import SimpleNamespace

import pytest

from corpus_structure.orchestrate.data_operations import _check_batch_active
from corpus_structure.semantic.claim_lifetime import (
    ClaimFenceLost,
    ClaimOwner,
    ClaimSettlementUncertain,
)


def claims():
    return tuple(
        SimpleNamespace(
            task_id=i, attempt=1, holder="worker", release_id="release", deadline=datetime.now(UTC)
        )
        for i in (1, 2)
    )


def test_lost_member_does_not_cancel_useful_batch_sibling():
    first, second = claims()
    owner = ClaimOwner(None, (first, second), "worker", None, lambda: None)
    owner.lost[(1, 1, "worker")] = ClaimFenceLost(first, "cancelled")
    del owner.active[(1, 1, "worker")]
    _check_batch_active(owner, (first, second))
    owner.lost[(2, 1, "worker")] = ClaimFenceLost(second, "fence")
    del owner.active[(2, 1, "worker")]
    with pytest.raises(ExceptionGroup) as raised:
        _check_batch_active(owner, (first, second))
    reasons = []
    for error in raised.value.exceptions:
        assert isinstance(error, ClaimFenceLost)
        reasons.append(error.reason)
    assert reasons == ["cancelled", "fence"]


def test_uncertain_batch_member_remains_uncertain_without_hiding_live_sibling():
    first, second = claims()
    owner = ClaimOwner(None, (first, second), "worker", None, lambda: None)
    uncertain = ClaimSettlementUncertain(first, "worker", b"intent")
    owner.uncertain[(1, 1, "worker")] = uncertain
    _check_batch_active(owner, (first, second))
    owner.lost[(2, 1, "worker")] = ClaimFenceLost(second, "revoked")
    del owner.active[(2, 1, "worker")]
    with pytest.raises(ExceptionGroup) as raised:
        _check_batch_active(owner, (first, second))
    assert raised.value.exceptions[0] is uncertain


def test_all_batch_claims_lost_during_owned_cpu_work_retire_process(tmp_path, monkeypatch):
    import copy

    from semantic.data_operation_port_support import fixture_source, kind, scope

    from corpus_structure.core.work import drive_prepared_work
    from corpus_structure.semantic import cpu_execution
    from corpus_structure.semantic.data_operation_ports import (
        PythonBatchMember,
        PythonRoleValue,
        resolve_python_port,
    )
    from corpus_structure.semantic.identity import claim_source_item__data_operation__

    metadata = copy.deepcopy(claim_source_item__data_operation__)
    metadata["capabilities"]["forms"] = ["batch"]
    model, sources = fixture_source(
        tmp_path,
        monkeypatch,
        "index: tuple[int, ...]",
        "while index:\n        index = index\n    return tuple(str(value) for value in index)",
        metadata=metadata,
        returns="tuple[str, ...]",
    )
    port = resolve_python_port(
        model, sources, model.operations[0].semantic_id, authorize=lambda _: None
    )
    first, second = claims()
    owner = ClaimOwner(None, (first, second), "worker", None, lambda: None)
    cpu = scope()
    processes = []
    monkeypatch.setattr(cpu_execution, "_COOPERATIVE_CLOSE_SECONDS", 0.1)
    monkeypatch.setattr(cpu_execution, "_WORKER_EXIT_SECONDS", 2.0)

    def active():
        if any(handle.future.running() for handle in tuple(cpu._handles)):
            if cpu._pool_ownership is not None:
                processes.extend(cpu._pool_ownership.processes)
            for claim in (first, second):
                key = (claim.task_id, claim.attempt, claim.holder)
                owner.active.pop(key, None)
                owner.lost[key] = ClaimFenceLost(claim, "cancelled")
        _check_batch_active(owner, (first, second))

    try:
        with pytest.raises(ExceptionGroup):
            drive_prepared_work(
                port.plan_batch_python(
                    tuple(
                        PythonBatchMember(
                            str(claim.task_id), (PythonRoleValue("index", kind(model, "index"), 1),)
                        )
                        for claim in (first, second)
                    ),
                    check_active=active,
                    execution_owner=SimpleNamespace(cpu=cpu, reservation=None),
                ),
                lambda: None,
            )
    finally:
        cpu.close()
    assert processes and all(not process.is_alive() for process in processes)
    assert cpu._physical_retired and cpu.budget.used_bytes == 0
