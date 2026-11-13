"""Physical retirement determines byte-credit release, including nested failures."""

from concurrent.futures import Future
from types import SimpleNamespace

import pytest

from corpus_structure.core.work import PhysicalRetirementUncertain
from corpus_structure.methods.native_host import NativeRetirementUncertain
from corpus_structure.orchestrate.data_operations import _InvocationExecution, _PythonWork
from corpus_structure.semantic.cpu_execution import OwnedByteBudget


@pytest.mark.parametrize("native", [False, True])
def test_nlp_drain_cannot_release_an_unproven_pdf_borrower(native):
    budget = OwnedByteBudget(100)
    reservation = budget.admit(100)
    future = Future()
    failure = (NativeRetirementUncertain if native else PhysicalRetirementUncertain)("still owned")
    future.set_exception(
        ExceptionGroup("calculation and teardown", [ValueError("calculation"), failure])
    )
    work = _PythonWork(future, reservation.release)
    assert not work.retire()
    assert budget.used_bytes == 100
    work.drained = True  # Proven NLP host-group death only.
    assert work.retire() is native
    assert budget.used_bytes == (0 if native else 100)
    if native:
        assert work.retire() and budget.used_bytes == 0


def test_provider_residents_follow_frozen_demand_not_all_available_factories():
    acquired = []
    declared = []

    def acquire(operation):
        if operation != "selected-provider":
            raise AssertionError("unrequested model assets were acquired")
        acquired.append(operation)
        return SimpleNamespace(native_selections=("selected-profile",))

    scope = _InvocationExecution.__new__(_InvocationExecution)
    scope.executor = SimpleNamespace(
        capability_factories={"selected-provider": object(), "unrequested-provider": object()},
        _port=acquire,
    )
    scope.native_hosts = SimpleNamespace(declare=declared.append)
    scope._selected_operations = None
    scope.select_operations(("pure-cpu", "selected-provider"))
    scope.select_operations(("selected-provider", "pure-cpu"))
    assert acquired == ["selected-provider"] and declared == [("selected-profile",)]
    with pytest.raises(ValueError, match="frozen operation closure"):
        scope.select_operations(("unrequested-provider",))
