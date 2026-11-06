"""Scheduling boundaries shared by the root and package test trees."""

import os
from collections.abc import Generator

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
    # Keep overlapping preparation tiers together; content-only and pure/cold controls
    # have no shared parse/scoping lifetime. Closure includes transitive fixture consumers.
    preparation = {
        "spike_readings",
        "spike_extraction",
        "spike_scoped",
        "s0r2_readings",
        "s0r2_extraction",
        "s0r2_scoped",
    }
    for item in items:
        if preparation.intersection(getattr(item, "fixturenames", ())):
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
