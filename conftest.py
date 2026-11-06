"""Scheduling boundaries shared by the root and package test trees."""

import os
from collections.abc import Generator
from pathlib import Path

import pytest


@pytest.hookimpl(tryfirst=True)
def pytest_configure(config: pytest.Config) -> None:
    # xdist allocates worker scratch before any descendant test conftest can help.
    if config.option.basetemp is not None or "PYTEST_DEBUG_TEMPROOT" in os.environ:
        return
    root = config.rootpath / "build" / "tmp" / "pytest"
    root.mkdir(parents=True, exist_ok=True)
    environment = pytest.MonkeyPatch()
    config.add_cleanup(environment.undo)
    environment.setenv("PYTEST_DEBUG_TEMPROOT", str(root))


@pytest.hookimpl(wrapper=True, tryfirst=True)
def pytest_collection_modifyitems(
    config: pytest.Config, items: list[pytest.Item]
) -> Generator[None]:
    # A session fixture is local to a worker. Keep the expensive corpus preparation and
    # its own bounded page pool together instead of rebuilding both on every auto-selected worker.
    math_tests = Path(__file__).parent / "python" / "corpus-structure" / "tests" / "math"
    for item in items:
        if item.path.is_relative_to(math_tests):
            item.add_marker(pytest.mark.xdist_group("math_preparation"))
    yield
    # Check after pytest's marker deselection: ordinary parallel runs omit these controls.
    faults = [item for item in items if item.get_closest_marker("shared_cluster_fault")]
    if faults and (config.getoption("numprocesses") or hasattr(config, "workerinput")):
        raise pytest.UsageError(
            "shared_cluster_fault controls require an exclusive serial invocation; "
            "use just test-native-faults (or -n 0 -m shared_cluster_fault)"
        )
    if faults and len(faults) != len(items):
        raise pytest.UsageError(
            "shared_cluster_fault controls must run separately from ordinary tests; "
            "use just test-native-faults"
        )
