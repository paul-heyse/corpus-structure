"""Scheduling boundaries shared by the root and package test trees."""

import os
from collections.abc import Generator

import pytest

from test_preparation import preparation_group


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
    for item in items:
        try:
            group = preparation_group(item)
        except pytest.UsageError as error:
            # xdist forwards collection reports but can schedule partial items
            # from a worker whose collection hook terminates with UsageError.
            items.clear()
            config.hook.pytest_collectreport(
                report=pytest.CollectReport(item.nodeid, "failed", str(error), [])
            )
            break
        if group is not None:
            item.own_markers[:] = [mark for mark in item.own_markers if mark.name != "xdist_group"]
            if not any(item.iter_markers("xdist_group")):
                item.add_marker(pytest.mark.xdist_group(group))
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
